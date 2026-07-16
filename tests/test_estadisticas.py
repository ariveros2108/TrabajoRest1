import pandas as pd
import pytest

from estadisticas import (
    calcular_estadisticas,
    aplicar_filtros,
    ValidacionError,
)


# --- cálculo ---

def test_calculo_basico():
    df = pd.DataFrame({"MONTO APLICADO": [10.0, 20.0, 30.0, 40.0, 50.0]})
    r = calcular_estadisticas(df)
    assert r["suma"] == 150.0
    assert r["conteo"] == 5
    assert r["promedio"] == 30.0
    assert r["minimo"] == 10.0
    assert r["maximo"] == 50.0
    assert r["mediana"] == 30.0


def test_mediana_par():
    df = pd.DataFrame({"MONTO APLICADO": [10.0, 20.0, 30.0, 40.0]})
    r = calcular_estadisticas(df)
    assert r["mediana"] == 25.0


def test_desviacion_estandar():
    df = pd.DataFrame({"MONTO APLICADO": [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]})
    r = calcular_estadisticas(df)
    assert r["promedio"] == 5.0
    assert r["desviacion_estandar"] == 2.0


def test_conjunto_vacio():
    df = pd.DataFrame({"MONTO APLICADO": []})
    r = calcular_estadisticas(df)
    assert r["conteo"] == 0
    assert r["suma"] == 0.0


# --- filtros y validación ---

@pytest.fixture
def df_ejemplo():
    return pd.DataFrame({
        "MONTO APLICADO": [100.0, 200.0, 300.0],
        "GENERO": [1, 2, 2],
        "CANAL": ["POS", "WEB", "POS"],
        "EDAD": pd.array([30, 40, 50], dtype="Int64"),
        "SKU": [201, 580, 201],
        "LOCAL": [1, 2, 1],
        "CODIGO CLIENTE": ["a", "b", "c"],
        "FECHA": pd.to_datetime(["2024-01-01", "2024-06-01", "2024-12-01"]),
    })


def test_filtro_genero_valido(df_ejemplo):
    resultado = aplicar_filtros(df_ejemplo, {"GENERO": "Femenino"})
    assert len(resultado) == 2


def test_filtro_canal_valido(df_ejemplo):
    resultado = aplicar_filtros(df_ejemplo, {"CANAL": "POS"})
    assert len(resultado) == 2


def test_genero_invalido_lanza_error(df_ejemplo):
    with pytest.raises(ValidacionError):
        aplicar_filtros(df_ejemplo, {"GENERO": "Inexistente"})


def test_canal_invalido_lanza_error(df_ejemplo):
    with pytest.raises(ValidacionError):
        aplicar_filtros(df_ejemplo, {"CANAL": "XYZ"})


def test_edad_no_convertible_lanza_error(df_ejemplo):
    with pytest.raises(ValidacionError):
        aplicar_filtros(df_ejemplo, {"EDAD": "treinta"})


def test_local_no_convertible_lanza_error(df_ejemplo):
    with pytest.raises(ValidacionError):
        aplicar_filtros(df_ejemplo, {"LOCAL": "abc"})


def test_filtro_invalido_lanza_error(df_ejemplo):
    with pytest.raises(ValidacionError):
        aplicar_filtros(df_ejemplo, {"COLOR": "azul"})
