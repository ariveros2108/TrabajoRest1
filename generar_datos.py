import json
import sys
import random
import uuid
from datetime import datetime, timedelta

# datos base
CANALES = ["POS", "WEB", "APP", "CCT", "APR", "WPR"]
GENEROS = [0, 1, 2, 3]
PRODUCTOS = [
    (201, "OLMEPRESS-D 20/12,5MG.30"),
    (580, "LEXAPRO COM.20MG.28"),
    (1095, "EUCERIN SERUM DERMOP.40ML"),
    (330, "PARACETAMOL 500MG.16"),
    (742, "IBUPROFENO 400MG.30"),
]
NOMBRES = ["ADRIANA", "SARA", "JUAN", "PEDRO", "LUISA", "CARLA", "MARIO"]
APELLIDOS = ["GURULE", "URBINA", "PÉREZ", "SOTO", "ROJAS", "MUÑOZ"]


def fecha_aleatoria(inicio, fin):
    delta = fin - inicio
    segundos = random.randint(0, int(delta.total_seconds()))
    return inicio + timedelta(seconds=segundos)


# genera un registro con las 15 columnas
def generar_registro():
    sku, producto = random.choice(PRODUCTOS)
    fecha = fecha_aleatoria(datetime(2023, 1, 1), datetime(2026, 6, 30))
    nacimiento = fecha_aleatoria(datetime(1950, 1, 1), datetime(2005, 12, 31))
    return {
        "FECHA": fecha.strftime("%Y-%m-%dT%H:%M:%S"),
        "CANAL": random.choice(CANALES),
        "SKU": sku,
        "PRODUCTO": producto,
        "UNIDADES": random.randint(1, 5),
        "PORCENTAJE DESCUENTO": round(random.uniform(0, 0.5), 4),
        "MONTO APLICADO": round(random.uniform(15, 226476), 2),
        "BOLETA": random.randint(1000000000, 1999999999),
        "LOCAL": random.randint(1, 500),
        "CODIGO CLIENTE": str(uuid.uuid4()),
        "RUN CLIENTE": f"{random.randint(1, 25)}.{random.randint(100, 999)}.{random.randint(100, 999)}-{random.randint(0, 9)}",
        "NOMBRES": random.choice(NOMBRES),
        "APELLIDOS": random.choice(APELLIDOS),
        "FECHA NACIMIENTO": nacimiento.strftime("%Y-%m-%d"),
        "GENERO": random.choice(GENEROS),
    }


def main():
    cantidad = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    registros = [generar_registro() for _ in range(cantidad)]
    with open("datos.json", "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)
    print(f"Generados {cantidad} registros en datos.json")


if __name__ == "__main__":
    main()
