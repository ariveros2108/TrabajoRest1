
Universidad Tecnológica Metropolitana — Computación Paralela y Distribuida.


## Requisitos

- Python 3.12 (probado en Ubuntu 24.04)

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requisitos.txt
```

## Obtención de datos

Con el entorno activado, descarga el dataset y lo descomprime como `datos.csv`:

```bash
python descargar_datos.py
```

## Ejecución

```bash
uvicorn main:app --reload
```

El CSV se carga en memoria al iniciar (unos segundos por el volumen).

- API: `http://127.0.0.1:8000/v1/estadisticas/ventas`
- Swagger: `http://127.0.0.1:8000/docs`

La ruta del CSV se puede cambiar con la variable `CSV_PATH`:

```bash
CSV_PATH=/otra/ruta.csv uvicorn main:app
```

## Uso

GET con filtros opcionales (query params):

```bash
curl "http://127.0.0.1:8000/v1/estadisticas/ventas"
curl "http://127.0.0.1:8000/v1/estadisticas/ventas?GENERO=Femenino&CANAL=POS"
```

POST con filtros en el body:

```bash
curl -X POST "http://127.0.0.1:8000/v1/estadisticas/ventas" \
  -H "Content-Type: application/json" \
  -d '{"consultas": [{"consulta": "GENERO", "valor": "Femenino"}]}'
```

Respuesta:

```json
{
  "suma": 33012425828.0,
  "conteo": 3242878,
  "promedio": 10179.98,
  "minimo": 15.0,
  "maximo": 226476.0,
  "mediana": 7662.0,
  "desviacion_estandar": 14453.24
}
```

## Filtros

GENERO, EDAD, CANAL, CODIGO_PRODUCTO, ID_PERSONA, LOCAL, FECHA_DESDE, FECHA_HASTA.

- GENERO: "No especificado", "Masculino", "Femenino", "Otro"
- CANAL: POS, WEB, APP, CCT, APR, WPR
- FECHA_DESDE / FECHA_HASTA en formato ISO-8601

Las consultas admiten cero, uno o varios filtros combinados.

## Errores

Todas las respuestas de error usan el mismo formato. El 400 (Validación Fallida,
`errorCode: "VF"`) cubre valores inválidos o no convertibles; el 500 (Error Interno,
`errorCode: "IE"`) cubre fallos internos.

## Pruebas

```bash
pytest -v
```

## Datos de prueba

`generar_datos.py` crea un `datos.json` con registros simulados:

```bash
python generar_datos.py 1000
```

## Estructura
main.py               API y endpoints
estadisticas.py       carga, filtrado y cálculo paralelo
errores.py            formato de errores 400/500
generar_datos.py      generador de datos.json
descargar_datos.py    descarga del dataset
tests/                pruebas unitarias
