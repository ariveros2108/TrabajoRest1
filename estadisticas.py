import os
import math
from datetime import date
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

# configuración del CSV
CSV_SEP = ";"
CSV_PATH = os.getenv("CSV_PATH", "datos.csv")
CHUNK_SIZE = 100_000

# GENERO viene como número, el filtro llega como texto
GENERO_TEXTO_A_NUM = {
    "No especificado": 0,
    "Masculino": 1,
    "Femenino": 2,
    "Otro": 3,
}

CANALES_VALIDOS = {"POS", "WEB", "APP", "CCT", "APR", "WPR"}

COLUMNAS_USADAS = [
    "FECHA", "CANAL", "SKU", "MONTO APLICADO",
    "LOCAL", "CODIGO CLIENTE", "FECHA NACIMIENTO", "GENERO",
]


def _procesar_chunk(chunk):
    chunk["MONTO APLICADO"] = pd.to_numeric(chunk["MONTO APLICADO"], errors="coerce")
    chunk["FECHA"] = pd.to_datetime(chunk["FECHA"], errors="coerce")
    chunk["FECHA NACIMIENTO"] = pd.to_datetime(chunk["FECHA NACIMIENTO"], errors="coerce")

    # edad por año/mes/día para evitar desbordes
    hoy = pd.Timestamp(date.today())
    nac = chunk["FECHA NACIMIENTO"]
    edad = hoy.year - nac.dt.year
    cumple_pasado = (nac.dt.month * 100 + nac.dt.day) <= (hoy.month * 100 + hoy.day)
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

    # procesa bloques en paralelo
    with ProcessPoolExecutor() as executor:
        procesados = list(executor.map(_procesar_chunk, chunks))

    return pd.concat(procesados, ignore_index=True)


class ValidacionError(Exception):
    pass


def aplicar_filtros(df, filtros):
    resultado = df

    for clave, valor in filtros.items():
        if valor is None:
            continue

        if clave == "GENERO":
            if valor not in GENERO_TEXTO_A_NUM:
                raise ValidacionError(f"El valor '{valor}' no es un género válido")
            resultado = resultado[resultado["GENERO"] == GENERO_TEXTO_A_NUM[valor]]

        elif clave == "EDAD":
            try:
                edad = int(valor)
            except (ValueError, TypeError):
                raise ValidacionError(f"El valor '{valor}' no es un número entero válido para EDAD")
            resultado = resultado[resultado["EDAD"] == edad]

        elif clave == "CANAL":
            if valor not in CANALES_VALIDOS:
                raise ValidacionError(f"El valor '{valor}' no es un canal válido")
            resultado = resultado[resultado["CANAL"] == valor]

        elif clave == "CODIGO_PRODUCTO":
            try:
                sku = int(valor)
            except (ValueError, TypeError):
                raise ValidacionError(f"El valor '{valor}' no es un SKU válido")
            resultado = resultado[resultado["SKU"] == sku]

        elif clave == "ID_PERSONA":
            resultado = resultado[resultado["CODIGO CLIENTE"] == str(valor)]

        elif clave == "LOCAL":
            try:
                local = int(valor)
            except (ValueError, TypeError):
                raise ValidacionError(f"El valor '{valor}' no es un número entero válido para LOCAL")
            resultado = resultado[resultado["LOCAL"] == local]

        elif clave == "FECHA_DESDE":
            try:
                fecha = pd.to_datetime(valor)
            except (ValueError, TypeError):
                raise ValidacionError(f"El valor '{valor}' no es una fecha ISO-8601 válida para FECHA_DESDE")
            resultado = resultado[resultado["FECHA"] >= fecha]

        elif clave == "FECHA_HASTA":
            try:
                fecha = pd.to_datetime(valor)
            except (ValueError, TypeError):
                raise ValidacionError(f"El valor '{valor}' no es una fecha ISO-8601 válida para FECHA_HASTA")
            resultado = resultado[resultado["FECHA"] <= fecha]

        else:
            raise ValidacionError(f"La consulta '{clave}' no es un filtro válido")

    return resultado


N_WORKERS = os.cpu_count() or 4


# map: agregados de una partición
def _reducir_particion(particion):
    return {
        "conteo": int(particion.size),
        "suma": float(particion.sum()),
        "suma_cuadrados": float((particion ** 2).sum()),
        "minimo": float(particion.min()),
        "maximo": float(particion.max()),
    }


def calcular_estadisticas(df):
    valores = df["MONTO APLICADO"].dropna().to_numpy(dtype=float)
    conteo = int(valores.size)

    if conteo == 0:
        return {
            "suma": 0.0, "conteo": 0, "promedio": 0.0,
            "minimo": 0.0, "maximo": 0.0, "mediana": 0.0,
            "desviacion_estandar": 0.0,
        }

    # paraleliza solo si conviene
    if conteo < 50_000:
        parciales = [_reducir_particion(valores)]
    else:
        particiones = np.array_split(valores, N_WORKERS)
        with ProcessPoolExecutor(max_workers=N_WORKERS) as executor:
            parciales = list(executor.map(_reducir_particion, particiones))

    # combina parciales
    suma = sum(p["suma"] for p in parciales)
    suma_cuadrados = sum(p["suma_cuadrados"] for p in parciales)
    minimo = min(p["minimo"] for p in parciales)
    maximo = max(p["maximo"] for p in parciales)

    promedio = suma / conteo
    varianza = max((suma_cuadrados / conteo) - (promedio ** 2), 0.0)
    desviacion = math.sqrt(varianza)

    # mediana necesita orden global
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
