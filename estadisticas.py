import os
import math
import uuid
from datetime import date
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd

CSV_SEP = ";"
CSV_PATH = os.getenv("CSV_PATH", "datos.csv")
CHUNK_SIZE = 100_000

GENERO_TEXTO_A_NUM = {
    "NO ESPECIFICADO": 0,
    "MASCULINO": 1,
    "FEMENINO": 2,
    "OTRO": 3,
}

CANALES_VALIDOS = {"POS", "WEB", "APP", "CCT", "APR", "WPR"}

COLUMNAS_USADAS = [
    "FECHA", "CANAL", "SKU", "MONTO APLICADO",
    "LOCAL", "CODIGO CLIENTE", "FECHA NACIMIENTO", "GENERO",
]

COLUMNAS_REQUERIDAS = [
    "MONTO APLICADO", "FECHA", "GENERO", "EDAD",
    "CANAL", "SKU", "CODIGO CLIENTE", "LOCAL",
]


def preparar_datos(chunk):
    chunk["MONTO APLICADO"] = pd.to_numeric(chunk["MONTO APLICADO"], errors="coerce")
    chunk["FECHA"] = pd.to_datetime(chunk["FECHA"], errors="coerce")
    chunk["FECHA NACIMIENTO"] = pd.to_datetime(chunk["FECHA NACIMIENTO"], errors="coerce")

    fecha_compra = chunk["FECHA"]
    nac = chunk["FECHA NACIMIENTO"]
    edad = fecha_compra.dt.year - nac.dt.year
    cumple_pasado = (nac.dt.month * 100 + nac.dt.day) <= (fecha_compra.dt.month * 100 + fecha_compra.dt.day)
    edad = edad - (~cumple_pasado).astype("Int64")
    chunk["EDAD"] = edad.astype("Int64")
    
    return chunk


def cargar_datos(path=CSV_PATH):
    lector = pd.read_csv(
        path,
        sep=CSV_SEP,
        usecols=COLUMNAS_USADAS,
        quotechar='"',
        chunksize=CHUNK_SIZE,
    )
    chunks = list(lector)

    with ProcessPoolExecutor() as executor:
        procesados = list(executor.map(preparar_datos, chunks))

    return pd.concat(procesados, ignore_index=True)


class ValidacionError(Exception):
    pass
    
def _parsear_entero(valor, nombre_filtro):
    try:
        return int(valor)
    except (ValueError, TypeError):
        raise ValidacionError(f"El valor '{valor}' no es un número entero válido para {nombre_filtro}")

def _parsear_fecha(valor, nombre_filtro):
    if str(valor).strip() == "":
        raise ValidacionError(f"El valor '{valor}' no es una fecha ISO-8601 válida para {nombre_filtro}")
    
    try:
        fecha = pd.to_datetime(valor)
        if pd.isna(fecha):
            raise ValueError
    except (ValueError, TypeError):
        raise ValidacionError(f"El valor '{valor}' no es una fecha ISO-8601 válida para {nombre_filtro}")
    
    if fecha.tzinfo is not None:
        fecha = fecha.tz_localize(None)
    
    return fecha


def aplicar_filtros(df: pd.DataFrame, filtros: Dict[str, Any]) -> pd.DataFrame:
    resultado = df

    for clave, valor in filtros.items():
        if valor is None:
            continue

        try:
            if clave == "GENERO":
                genero_normalizado = " ".join(str(valor).split()).upper()
                
                reemplazos_tildes = {"Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U"}
                for con_tilde, sin_tilde in reemplazos_tildes.items():
                    genero_normalizado = genero_normalizado.replace(con_tilde, sin_tilde)

                if genero_normalizado not in GENERO_TEXTO_A_NUM:
                    raise ValidacionError(f"El valor '{valor}' no es un género válido")
                resultado = resultado[resultado["GENERO"] == GENERO_TEXTO_A_NUM[genero_normalizado]]

            elif clave == "EDAD":
                edad = _parsear_entero(valor, "EDAD")
                resultado = resultado[resultado["EDAD"] == edad]

            elif clave == "CANAL":
                canal_normalizado = str(valor).strip().upper()
                if canal_normalizado not in CANALES_VALIDOS:
                    raise ValidacionError(f"El valor '{valor}' no es un canal válido")
                resultado = resultado[resultado["CANAL"] == canal_normalizado]

            elif clave == "CODIGO_PRODUCTO":
                sku = _parsear_entero(valor, "CODIGO_PRODUCTO")
                resultado = resultado[resultado["SKU"] == sku]

            elif clave == "ID_PERSONA":
                try:
                    uuid_normalizado = uuid.UUID(str(valor))
                except (ValueError, AttributeError, TypeError):
                    raise ValidacionError(f"El valor '{valor}' no es un ID_PERSONA (UUID) válido")
                resultado = resultado[resultado["CODIGO CLIENTE"] == str(uuid_normalizado)]

            elif clave == "LOCAL":
                local = _parsear_entero(valor, "LOCAL")
                resultado = resultado[resultado["LOCAL"] == local]

            elif clave == "FECHA_DESDE":
                fecha = _parsear_fecha(valor, "FECHA_DESDE")
                resultado = resultado[resultado["FECHA"] >= fecha]

            elif clave == "FECHA_HASTA":
                fecha = _parsear_fecha(valor, "FECHA_HASTA")
                resultado = resultado[resultado["FECHA"] <= fecha]

            else:
                raise ValidacionError(f"La consulta '{clave}' no es un filtro válido")

        except ValidacionError:
            raise

    return resultado


N_WORKERS = os.cpu_count() or 4


def _reducir_particion(particion):
    return {
        "conteo": int(particion.size),
        "suma": float(particion.sum()),
        "suma_cuadrados": float((particion ** 2).sum()),
        "minimo": float(particion.min()),
        "maximo": float(particion.max()),
    }


def calcular_estadisticas(df: pd.DataFrame, pool_executor: Optional[ProcessPoolExecutor] = None) -> Dict[str, float | int]:
    valores = df["MONTO APLICADO"].dropna().to_numpy(dtype=float)
    conteo = int(valores.size)

    if conteo == 0:
        return {
            "suma": 0.0, "conteo": 0, "promedio": 0.0,
            "minimo": 0.0, "maximo": 0.0, "mediana": 0.0,
            "desviacion_estandar": 0.0,
        }

    if conteo < 50_000:
        parciales = [_reducir_particion(valores)]
    else:
        particiones = np.array_split(valores, N_WORKERS)
        
        if pool_executor is not None:
            parciales = list(pool_executor.map(_reducir_particion, particiones))
        else:
            with ProcessPoolExecutor(max_workers=N_WORKERS) as executor:
                parciales = list(executor.map(_reducir_particion, particiones))

    suma = sum(p["suma"] for p in parciales)
    suma_cuadrados = sum(p["suma_cuadrados"] for p in parciales)
    minimo = min(p["minimo"] for p in parciales)
    maximo = max(p["maximo"] for p in parciales)

    promedio = suma / conteo
    varianza = max((suma_cuadrados / conteo) - (promedio ** 2), 0.0)
    desviacion = math.sqrt(varianza)

    mediana = float(np.median(valores))

    return {
        "suma": round(suma, 2),
        "conteo": conteo,
        "promedio": round(promedio, 2),
        "minimo": round(minimo, 2),
        "maximo": round(maximo, 2),
        "mediana": round(mediana, 2),
        "desviacion_estandar": round(desviacion, 2),
    }