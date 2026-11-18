#!/usr/bin/env python3

import csv
import math
import subprocess
import time
from pathlib import Path

BASE = Path.home() / "agv_predictivo"

MATRIZ = (
    BASE / "entrega_avance2/experimentos/"
    "matriz_20_ensayos.csv"
)

SALIDA = (
    BASE / "entrega_avance2/evidencias/"
    "preparacion_20_ensayos_gazebo.csv"
)

MODELO = "turtlebot3_waffle"

# Punto de aproximación E1.
PRE_X = 0.65
PRE_Y = -1.40

# Orientación nominal hacia la estación.
YAW_BASE = 0.0

# Altura de colocación del modelo.
Z = 0.10


def ejecutar(comando, timeout=15):
    return subprocess.run(
        comando,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False
    )


def colocar_robot(x, y, yaw):
    comando = [
        "gz", "model",
        "-m", MODELO,
        "-x", str(x),
        "-y", str(y),
        "-z", str(Z),
        "-R", "0",
        "-P", "0",
        "-Y", str(yaw),
    ]

    resultado = ejecutar(comando)

    if resultado.returncode != 0:
        raise RuntimeError(
            resultado.stderr or resultado.stdout
        )

    return resultado


def consultar_robot():
    resultado = ejecutar([
        "gz", "model",
        "-m", MODELO,
        "-p"
    ])

    if resultado.returncode != 0:
        raise RuntimeError(
            resultado.stderr or resultado.stdout
        )

    return resultado.stdout.strip()


def configuracion(escenario):
    if escenario == "frontal":
        return PRE_X, PRE_Y, 0.0

    if escenario == "desalineacion_15":
        return PRE_X, PRE_Y, math.radians(15)

    if escenario == "error_supervisor":
        return (
            PRE_X,
            PRE_Y + 0.03,
            math.radians(10)
        )

    if escenario == "perturbacion_lateral":
        return PRE_X, PRE_Y, 0.0

    raise ValueError(
        f"Escenario desconocido: {escenario}"
    )


def main():
    with MATRIZ.open(newline="") as archivo:
        ensayos = list(csv.DictReader(archivo))

    print("=" * 55)
    print("PREPARACION DE 20 ENSAYOS EN GAZEBO")
    print("=" * 55)
    print("Total de ensayos:", len(ensayos))
    print("Robot:", MODELO)
    print("Estacion: E1")
    print()

    if len(ensayos) != 20:
        raise RuntimeError(
            "La matriz no contiene exactamente 20 ensayos"
        )

    # Solo se modifica la posición del modelo.
    # No se publican comandos de velocidad.
    # No se modifica el árbitro STOP.

    registros = []

    try:
        for indice, ensayo in enumerate(ensayos, 1):
            escenario = ensayo["escenario"]
            repeticion = ensayo["repeticion"]

            x, y, yaw = configuracion(escenario)

            print(
                f"[{indice}/20] "
                f"{escenario} - repeticion {repeticion}"
            )

            colocar_robot(x, y, yaw)

            # Tiempo para observar el escenario en Gazebo.
            time.sleep(2.0)

            pose = consultar_robot()

            print("  Pose Gazebo:", pose)

            registros.append({
                "escenario": escenario,
                "repeticion": repeticion,
                "x_inicial_m": x,
                "y_inicial_m": y,
                "yaw_inicial_grados": math.degrees(yaw),
                "pose_observada_gazebo": pose,
                "estado": "ESCENARIO_PREPARADO",
                "acople_ejecutado": "NO",
                "acople_exitoso": "",
                "observaciones": (
                    "Configuracion inicial en Gazebo; "
                    "sin movimiento de acoplamiento"
                ),
            })

            print()

    except KeyboardInterrupt:
        print("\nPreparacion interrumpida por el usuario.")

    except Exception as error:
        print("\nERROR:", error)

    finally:
        SALIDA.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        columnas = [
            "escenario",
            "repeticion",
            "x_inicial_m",
            "y_inicial_m",
            "yaw_inicial_grados",
            "pose_observada_gazebo",
            "estado",
            "acople_ejecutado",
            "acople_exitoso",
            "observaciones",
        ]

        with SALIDA.open("w", newline="") as archivo:
            escritor = csv.DictWriter(
                archivo,
                fieldnames=columnas
            )
            escritor.writeheader()
            escritor.writerows(registros)

        print("=" * 55)
        print("REGISTROS GUARDADOS:", len(registros))
        print("ARCHIVO:", SALIDA)
        print("=" * 55)


if __name__ == "__main__":
    main()
