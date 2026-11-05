
#!/usr/bin/env python3

import csv
from pathlib import Path
from math import hypot, isfinite

BASE = Path.home() / "agv_predictivo"
DATOS = BASE / "datos"

NOMBRES = ["Base", "E1", "E2", "E3", "E4", "E5"]

def leer_csv(ruta):
    if not ruta.is_file():
        raise FileNotFoundError(f"Falta el archivo: {ruta}")

    with ruta.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def main():
    matriz = leer_csv(DATOS / "matriz_distancias.csv")
    objetivos = leer_csv(DATOS / "objetivos_navegacion.csv")

    assert len(matriz) == 6, "La matriz debe tener 6 filas"
    assert len(objetivos) == 5, "Deben existir 5 objetivos"

    destinos = {}

    for fila in objetivos:
        nombre = f"E{int(fila['estacion'])}"
        destinos[nombre] = (
            float(fila["x"]),
            float(fila["y"])
        )

    print("\nVALIDACION DE RUTAS MATLAB -> ROS 2")
    print("-" * 45)

    total = 0

    for origen in NOMBRES:
        for destino in NOMBRES:
            if origen == destino:
                continue

            archivo = DATOS / f"ruta_{origen}_{destino}.csv"
            ruta = leer_csv(archivo)

            if len(ruta) < 2:
                raise ValueError(f"Ruta vacia: {archivo.name}")

            puntos = [
                (float(f["x"]), float(f["y"]))
                for f in ruta
            ]

            if not all(
                isfinite(x) and isfinite(y)
                for x, y in puntos
            ):
                raise ValueError(f"Coordenadas invalidas: {archivo.name}")

            longitud = sum(
                hypot(b[0]-a[0], b[1]-a[1])
                for a, b in zip(puntos, puntos[1:])
            )

            if destino in destinos:
                error = hypot(
                    puntos[-1][0] - destinos[destino][0],
                    puntos[-1][1] - destinos[destino][1]
                )

                if error > 0.001:
                    raise ValueError(
                        f"Destino incorrecto en {archivo.name}"
                    )

            print(
                f"{origen:4s} -> {destino:4s}: "
                f"{longitud:.3f} m | "
                f"{len(puntos)} puntos"
            )

            total += 1

    print("-" * 45)
    print(f"Rutas verificadas: {total}/30")
    print("Archivos preparados para integracion ROS 2")

if __name__ == "__main__":
    main()
