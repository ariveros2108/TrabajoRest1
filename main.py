import logging
import time
from contextlib import asynccontextmanager
from typing import Optional, List
from concurrent.futures import ProcessPoolExecutor

from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field

import pandas as pd

import estadisticas
from estadisticas import (
    cargar_datos,
    aplicar_filtros,
    calcular_estadisticas,
    ValidacionError,
)
from errores import error_400, error_500, error_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

datos = {"df": None, "executor": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando ProcessPoolExecutor con {estadisticas.N_WORKERS} workers...")
    datos["executor"] = ProcessPoolExecutor(max_workers=estadisticas.N_WORKERS)
    
    logger.info("Cargando CSV en memoria...")
    inicio = time.time()
    try:
        datos["df"] = cargar_datos(estadisticas.CSV_PATH)
        logger.info(f"Carga completa: {len(datos['df'])} filas en {round(time.time() - inicio, 2)}s.")
    except Exception as e:
        logger.error(f"Error al cargar el CSV: {e}")
        try:
            crudo = pd.read_json("datos.json")
            datos["df"] = estadisticas.preparar_datos(crudo)
            logger.info(f"Respaldo cargado: {len(datos['df'])} filas desde datos.json.")
        except Exception as e2:
            datos["df"] = pd.DataFrame(columns=estadisticas.COLUMNAS_REQUERIDAS)
            logger.warning(f"Sin datos disponibles ({e2}), se inicia vacío.")
    
    yield
    
    logger.info("Apagando servidor: liberando memoria y cerrando pool de procesos.")
    datos["df"] = None
    if datos["executor"] is not None:
        datos["executor"].shutdown(wait=True)
        datos["executor"] = None


app = FastAPI(
    title="Cruz Morada - Servicio de Estadísticas de Ventas",
    description="API REST para obtener un resumen estadístico de ventas.",
    version="1.0.0",
    lifespan=lifespan,
)

RUTA_BASE = "/v1/estadisticas/ventas"


class Consulta(BaseModel):
    consulta: str = Field(..., description="Nombre del filtro (ej. GENERO, CANAL)")
    valor: str = Field(..., description="Valor a filtrar")


class CuerpoPost(BaseModel):
    consultas: List[Consulta]

    model_config = {
        "json_schema_extra": {
            "example": {
                "consultas": [
                    {"consulta": "GENERO", "valor": "Femenino"},
                    {"consulta": "EDAD", "valor": "31"},
                    {"consulta": "CANAL", "valor": "POS"},
                ]
            }
        }
    }


class EstadisticasResponse(BaseModel):
    suma: float
    conteo: int
    promedio: float
    minimo: float
    maximo: float
    mediana: float
    desviacion_estandar: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "suma": 1500.5,
                "conteo": 42,
                "promedio": 35.73,
                "minimo": 10.0,
                "maximo": 100.0,
                "mediana": 30.0,
                "desviacion_estandar": 25.4,
            }
        }
    }


RESPUESTAS_ERROR = {
    400: {
        "description": "Filtro o valor inválido",
        "content": {
            "application/json": {
                "example": error_400(
                    "El valor 'qwerqwer' no es un número entero válido para el ID de tienda", "POST"
                )
            }
        },
    },
    500: {
        "description": "Error interno del servidor",
        "content": {
            "application/json": {
                "example": error_500("Error al calcular la desviación estándar", "GET")
            }
        },
    },
}


@app.exception_handler(RequestValidationError)
async def handler_validacion(request: Request, exc: RequestValidationError):
    metodo = request.method
    try:
        primer_error = exc.errors()[0]
        campo = ".".join(str(x) for x in primer_error.get("loc", []))
        mensaje = primer_error.get("msg", "Error de validación")
        detalle = f"Error de validación en '{campo}': {mensaje}"
    except (IndexError, KeyError):
        detalle = "El cuerpo de la solicitud no es válido"
    return JSONResponse(status_code=400, content=error_400(detalle, metodo))


@app.exception_handler(StarletteHTTPException)
async def handler_http_exception(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.status_code, str(exc.detail), request.method),
    )

@app.exception_handler(Exception)
async def handler_excepcion_generica(request: Request, exc: Exception):
    logger.exception("Excepción no controlada")
    return JSONResponse(
        status_code=500,
        content=error_500(f"Error interno no controlado: {exc}", request.method),
    )


def procesar(filtros, method):
    df = datos["df"]
    executor = datos.get("executor")
    
    if df is None:
        return JSONResponse(status_code=500, content=error_500("Los datos no están cargados", method))
    try:
        filtrado = aplicar_filtros(df, filtros)
        resultado = calcular_estadisticas(filtrado, pool_executor=executor)
        return JSONResponse(status_code=200, content=resultado)
    except ValidacionError as e:
        return JSONResponse(status_code=400, content=error_400(str(e), method))
    except Exception as e:
        return JSONResponse(status_code=500, content=error_500(str(e), method))


@app.get(
    RUTA_BASE,
    response_model=EstadisticasResponse,
    responses=RESPUESTAS_ERROR,
    summary="Estadísticas de ventas con filtros opcionales por query params",
    description="Devuelve suma, conteo, promedio, mínimo, máximo, mediana y "
    "desviación estándar de MONTO APLICADO, filtrando opcionalmente por "
    "GENERO, EDAD, CANAL, CODIGO_PRODUCTO, ID_PERSONA, LOCAL, FECHA_DESDE y/o FECHA_HASTA.",
)
def get_estadisticas(
    request: Request,
    GENERO: Optional[str] = Query(None, description="Femenino, Masculino, Otro o 'No especificado'"),
    EDAD: Optional[str] = Query(None, description="Edad exacta a consultar (entero)"),
    CANAL: Optional[str] = Query(None, description="POS, WEB, APP, CCT, APR o WPR"),
    CODIGO_PRODUCTO: Optional[str] = Query(None, description="SKU del producto"),
    ID_PERSONA: Optional[str] = Query(None, description="UUID del cliente"),
    LOCAL: Optional[str] = Query(None, description="Número de local"),
    FECHA_DESDE: Optional[str] = Query(None, description="Fecha mínima, ISO-8601"),
    FECHA_HASTA: Optional[str] = Query(None, description="Fecha máxima, ISO-8601"),
):
    filtros = dict(request.query_params)
    return procesar(filtros, "GET")


@app.post(
    RUTA_BASE,
    response_model=EstadisticasResponse,
    responses=RESPUESTAS_ERROR,
    summary="Estadísticas de ventas con filtros personalizados",
    description="Igual que el GET, pero los filtros se envían en el cuerpo "
    "como una lista de pares {consulta, valor}. Se puede incluir cualquier "
    "cantidad arbitraria de filtros distintos.",
)
def post_estadisticas(cuerpo: CuerpoPost):
    if not cuerpo.consultas:
        return JSONResponse(
            status_code=400, 
            content=error_400("El arreglo 'consultas' no puede estar vacío", "POST")
        )
    filtros = {item.consulta: item.valor for item in cuerpo.consultas}

    return procesar(filtros, "POST")