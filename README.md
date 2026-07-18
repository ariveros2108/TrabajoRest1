# Cruz Morada — Servicio de Estadísticas de Ventas

Universidad Tecnológica Metropolitana — Computación Paralela y Distribuida.
Alexander Riveros Avila
Sebastian Antileo Antileo
Sebastian inzulza


API REST que entrega un resumen estadístico (suma, conteo, promedio, mínimo, máximo, mediana y desviación estándar) sobre el histórico de ventas de Cruz Morada, con carga paralela de datos y filtros opcionales por género, edad, canal, producto, cliente, local y rango de fechas.

## Características

- Carga de datos **paralela y desatendida** al iniciar el servidor: el CSV se lee en chunks y cada chunk se preprocesa en un proceso independiente.
- Cálculo de estadísticas mediante **reducción paralela** (map-reduce): los agregados se calculan por partición y se combinan al final.
- Filtros opcionales vía **query params (GET)** o **cuerpo JSON (POST)**, con validación estricta.
- Errores siempre en el formato estandarizado que exige la pauta.
- Documentación interactiva automática (Swagger / ReDoc).

## Requisitos

- Python 3.10 o superior.
- Dependencias: `fastapi`, `uvicorn`, `pydantic`, `pandas`, `numpy`.

```bash
pip install fastapi uvicorn pandas numpy
```

## Preparar los datos

El servicio espera un CSV **separado por `;`** con las columnas del dataset de Cruz Morada (`FECHA`, `CANAL`, `SKU`, `MONTO APLICADO`, `LOCAL`, `CODIGO CLIENTE`, `FECHA NACIMIENTO`, `GENERO`, entre otras).

1. Coloca el archivo como `datos.csv` en la raíz del proyecto, o apunta a otra ruta con una variable de entorno:

   ```bash
   export CSV_PATH=/ruta/a/tu/archivo.csv
   ```

   Si cuentas con un script de descarga del dataset real (por ejemplo `descargar_datos.py`), ejecútalo primero para dejar `datos.csv` listo.

2. Si no tienes el CSV real a mano, genera datos de prueba sintéticos:

   ```bash
   python generar_datos.py 1000   # crea datos.json con 1000 registros de ejemplo
   ```

Si `datos.csv` no existe o falla la carga, el servidor cae automáticamente a `datos.json` como respaldo. Si tampoco hay `datos.json`, arranca con un dataset vacío en vez de caerse.

## Ejecutar el servidor

```bash
uvicorn main:app --reload
```

La carga de datos ocurre **una sola vez**, al arrancar el servidor, no en cada consulta.

Con el servidor corriendo:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoint

```
GET  /v1/estadisticas/ventas
POST /v1/estadisticas/ventas
```

Ambos devuelven el mismo resumen estadístico sobre `MONTO APLICADO`. Sin filtros, el cálculo es sobre el dataset completo.

### Filtros soportados

| Filtro | Valores válidos |
|---|---|
| `GENERO` | `Femenino`, `Masculino`, `Otro`, `No especificado` (sin distinguir mayúsculas ni tildes) |
| `EDAD` | Entero. Es la edad del cliente **al momento de la compra**, no su edad actual |
| `CANAL` | `POS`, `WEB`, `APP`, `CCT`, `APR`, `WPR` |
| `CODIGO_PRODUCTO` | Entero (SKU del producto) |
| `ID_PERSONA` | UUID del cliente |
| `LOCAL` | Entero (número de local) |
| `FECHA_DESDE` | Fecha ISO-8601 |
| `FECHA_HASTA` | Fecha ISO-8601 |

Se pueden combinar cualquier cantidad de filtros, o no usar ninguno. Un filtro fuera de esta lista, o un valor que no se pueda interpretar en el tipo esperado, responde con `400`.

### GET — ejemplo

```bash
curl "http://localhost:8000/v1/estadisticas/ventas?GENERO=Femenino&EDAD=31&CANAL=POS"
```

### POST — ejemplo

```bash
curl -X POST "http://localhost:8000/v1/estadisticas/ventas" \
  -H "Content-Type: application/json" \
  -d '{
    "consultas": [
      {"consulta": "GENERO", "valor": "Femenino"},
      {"consulta": "EDAD", "valor": "31"},
      {"consulta": "CANAL", "valor": "POS"}
    ]
  }'
```

### Respuesta exitosa (200)

```json
{
  "suma": 1500.5,
  "conteo": 42,
  "promedio": 35.73,
  "minimo": 10.0,
  "maximo": 100.0,
  "mediana": 30.0,
  "desviacion_estandar": 25.4
}
```

### Formato de error

Toda respuesta de error (400 o 500) sigue esta misma estructura:

```json
{
  "detail": "El valor 'TELEFONO' no es un canal válido",
  "instance": "/v1/estadisticas/ventas",
  "status": 400,
  "title": "Bad Request",
  "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400",
  "timestamp": "2026-07-18T04:15:23.456789Z",
  "errorCode": "VF",
  "errorLabel": "Validación Fallida",
  "method": "GET"
}
```

Causas de `400`:
- El arreglo `consultas` viene vacío o nulo (POST).
- Se envía un filtro que no está en la lista de filtros soportados.
- El valor de un filtro no se puede convertir al tipo esperado (por ejemplo `EDAD=treinta`, un `ID_PERSONA` que no es un UUID válido, o un `CANAL` fuera de la lista).

Un `500` indica un error interno no controlado durante el procesamiento.

## Procesamiento paralelo

- **Carga**: el CSV se lee en chunks de 100.000 filas; cada chunk se preprocesa (parseo de fechas, cálculo de `EDAD`) en un proceso independiente vía `ProcessPoolExecutor`, y luego se concatenan en un único `DataFrame` que queda en memoria para todas las consultas.
- **Cálculo de estadísticas**: si el resultado filtrado supera 50.000 filas, el arreglo de montos se reparte entre `os.cpu_count()` procesos. Cada uno calcula su propio conteo, suma, suma de cuadrados, mínimo y máximo; esos valores parciales se combinan al final para obtener el resultado global. La mediana se calcula aparte, sobre el arreglo completo, porque no se puede reconstruir correctamente a partir de medianas parciales.

## Estructura del proyecto

| Archivo | Contenido |
|---|---|
| `main.py` | Aplicación FastAPI: ciclo de vida (carga de datos), endpoints GET/POST, manejadores de error. |
| `estadisticas.py` | Carga y preprocesamiento del CSV, aplicación de filtros, cálculo de estadísticas. |
| `errores.py` | Construcción del cuerpo de error estándar. |
| `generar_datos.py` | Genera `datos.json`, un set de datos de prueba sintético. |
| `conftest.py` | Configuración de `pytest`. |
| `datos.json` | Datos de prueba (salida de `generar_datos.py`). |

## Pruebas

```bash
pytest
```
