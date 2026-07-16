from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

import estadisticas
from estadisticas import (
    cargar_datos,
    aplicar_filtros,
    calcular_estadisticas,
    ValidacionError,
)
from errores import error_400, error_500

datos = {"df": None}


# carga desatendida al iniciar
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Cargando CSV en memoria...")
    datos["df"] = cargar_datos(estadisticas.CSV_PATH)
    print(f"Carga completa: {len(datos['df'])} filas.")
    yield
    datos["df"] = None


app = FastAPI(
    title="Cruz Morada - Servicio de Estadísticas de Ventas",
    description="API REST para obtener un resumen estadístico de ventas.",
    version="1.0.0",
    lifespan=lifespan,
)

RUTA_BASE = "/v1/estadisticas/ventas"

FILTROS_VALIDOS = {
    "GENERO", "EDAD", "CANAL", "CODIGO_PRODUCTO",
    "ID_PERSONA", "LOCAL", "FECHA_DESDE", "FECHA_HASTA",
}


class Consulta(BaseModel):
    consulta: str
    valor: str


class CuerpoPost(BaseModel):
    consultas: List[Consulta]


# convierte los 422 de FastAPI al formato 400
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


def procesar(filtros, method):
    df = datos["df"]
    if df is None:
        return JSONResponse(status_code=500, content=error_500("Los datos no están cargados", method))
    try:
        filtrado = aplicar_filtros(df, filtros)
        resultado = calcular_estadisticas(filtrado)
        return JSONResponse(status_code=200, content=resultado)
    except ValidacionError as e:
        return JSONResponse(status_code=400, content=error_400(str(e), method))
    except Exception as e:
        return JSONResponse(status_code=500, content=error_500(str(e), method))


@app.get(RUTA_BASE)
def get_estadisticas(
    GENERO: Optional[str] = Query(None),
    EDAD: Optional[str] = Query(None),
    CANAL: Optional[str] = Query(None),
    CODIGO_PRODUCTO: Optional[str] = Query(None),
    ID_PERSONA: Optional[str] = Query(None),
    LOCAL: Optional[str] = Query(None),
    FECHA_DESDE: Optional[str] = Query(None),
    FECHA_HASTA: Optional[str] = Query(None),
):
    filtros = {
        "GENERO": GENERO, "EDAD": EDAD, "CANAL": CANAL,
        "CODIGO_PRODUCTO": CODIGO_PRODUCTO, "ID_PERSONA": ID_PERSONA,
        "LOCAL": LOCAL, "FECHA_DESDE": FECHA_DESDE, "FECHA_HASTA": FECHA_HASTA,
    }
    return procesar(filtros, "GET")


@app.post(RUTA_BASE)
def post_estadisticas(cuerpo: CuerpoPost):
    if not cuerpo.consultas:
        return JSONResponse(status_code=400, content=error_400("El arreglo 'consultas' no puede estar vacío", "POST"))

    filtros = {}
    for item in cuerpo.consultas:
        clave = item.consulta
        if clave not in FILTROS_VALIDOS:
            return JSONResponse(
                status_code=400,
                content=error_400(f"La consulta '{clave}' no es uno de los valores permitidos", "POST"),
            )
        filtros[clave] = item.valor

    return procesar(filtros, "POST")
