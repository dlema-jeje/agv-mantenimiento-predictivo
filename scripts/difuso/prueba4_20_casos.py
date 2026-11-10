#!/usr/bin/env python3
"""Prueba 4: matriz 4 x 5 del controlador Mamdani calibrado.

Evaluacion offline: no inicializa ROS2 ni publica velocidades.
"""

import csv
import math
from pathlib import Path

from controlador_agv_calibrado import crear_simulacion


DISTANCIAS = [0.00, 0.05, 0.15, 0.35]
ANGULOS = [-15.0, -5.0, 0.0, 5.0, 15.0]

V_MIN = -0.05
V_MAX = 0.15
W_MIN = -0.8
W_MAX = 0.8

SALIDA = Path("resultados/prueba4_20_casos.csv")


def ejecutar():
    resultados = []
    aprobados = 0

    print("=" * 78)
    print("PRUEBA 4 - CONTROLADOR MAMDANI CALIBRADO")
    print("20 casos: 4 distancias x 5 errores angulares")
    print("MODO OFFLINE: SIN MOVIMIENTO")
    print("=" * 78)

    print(
        f"{'CASO':<7}"
        f"{'ed (m)':>10}"
        f"{'et (°)':>10}"
        f"{'v (m/s)':>14}"
        f"{'w (rad/s)':>14}"
        f"{'ESTADO':>14}"
    )

    for distancia in DISTANCIAS:
        for angulo in ANGULOS:
            numero = len(resultados) + 1

            v = float("nan")
            w = float("nan")
            error = ""

            try:
                simulacion = crear_simulacion()

                simulacion.input["ed"] = distancia
                simulacion.input["et"] = angulo
                simulacion.compute()

                v = float(simulacion.output["v"])
                w = float(simulacion.output["w"])

                valido = (
                    math.isfinite(v)
                    and math.isfinite(w)
                    and V_MIN - 1e-9 <= v <= V_MAX + 1e-9
                    and W_MIN - 1e-9 <= w <= W_MAX + 1e-9
                )

            except Exception as exc:
                valido = False
                error = str(exc)

            estado = "APROBADO" if valido else "FALLIDO"

            if valido:
                aprobados += 1

            resultados.append({
                "caso": numero,
                "ed_m": distancia,
                "et_grados": angulo,
                "v_m_s": v,
                "w_rad_s": w,
                "estado": estado,
                "error": error,
            })

            print(
                f"{numero:<7}"
                f"{distancia:>10.3f}"
                f"{angulo:>10.1f}"
                f"{v:>14.6f}"
                f"{w:>14.6f}"
                f"{estado:>14}"
            )

    SALIDA.parent.mkdir(parents=True, exist_ok=True)

    with SALIDA.open("w", newline="") as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=[
                "caso",
                "ed_m",
                "et_grados",
                "v_m_s",
                "w_rad_s",
                "estado",
                "error",
            ],
        )
        escritor.writeheader()
        escritor.writerows(resultados)

    print("=" * 78)
    print(f"CASOS EVALUADOS: {len(resultados)}")
    print(f"APROBADOS: {aprobados}")
    print(f"FALLIDOS: {len(resultados) - aprobados}")
    print(f"CSV: {SALIDA}")
    print("=" * 78)

    if aprobados != len(resultados):
        raise SystemExit(1)


if __name__ == "__main__":
    ejecutar()
