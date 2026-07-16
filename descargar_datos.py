import gzip
import os
import shutil

import gdown


FILE_ID = "1VKSfe-CyzSY2WwOAcUFNi4PG0A9CdvdO"
ARCHIVO_GZ = "datos.csv.gz"
ARCHIVO_CSV = "datos.csv"


def descargar():
    print("Descargando dataset desde Google Drive")
    gdown.download(id=FILE_ID, output=ARCHIVO_GZ, quiet=False)


# descomprime el .gz a .csv
def descomprimir():
    print("Descomprimiendo")
    with gzip.open(ARCHIVO_GZ, "rb") as f_in:
        with open(ARCHIVO_CSV, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


def main():
    if os.path.exists(ARCHIVO_CSV):
        print(f"'{ARCHIVO_CSV}' ya existe.")
        return
    descargar()
    descomprimir()
    if os.path.exists(ARCHIVO_GZ):
        os.remove(ARCHIVO_GZ)
    print("Siga con uvicorn main:app")


if __name__ == "__main__":
    main()
