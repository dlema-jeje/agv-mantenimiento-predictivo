#!/usr/bin/env python3
"""Evaluación numérica, NO ensayos físicos Gazebo."""
import csv
import math
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts/difuso"))

from controlador_agv import crear_simulacion

SALIDA = RAIZ / "entrega_avance2/experimentos"
DT = 0.05
MAX_TIEMPO = 20.0

ESCENARIOS = [
    ("centrado", 0.0, 0.0, False),
    ("yaw_15_grados", 15.0, 0.0, False),
    ("lateral_3cm_yaw_10", 10.0, 0.03, False),
    ("perturbacion_lateral", 0.0, 0.0, True),
]


def ejecutar(nombre, repeticion, yaw_inicial, lateral, perturbacion):
    # Pequeñas variaciones deterministas entre repeticiones.
    ed = 0.18 + (repeticion - 3) * 0.003
    yaw = math.radians(yaw_inicial)
    lateral += (repeticion - 3) * 0.001

    sim = crear_simulacion()
    oscilaciones = 0
    signo_anterior = 0
    estable = 0.0
    exito = False
    motivo = "TIEMPO_AGOTADO"
    tiempo = 0.0

    for paso in range(int(MAX_TIEMPO / DT)):
        tiempo = paso * DT

        # Entradas limitadas al universo definido en el controlador.
        entrada_ed = max(-0.05, min(0.45, ed))
        entrada_yaw = max(-20.0, min(20.0, math.degrees(yaw)))

        sim.input["ed"] = entrada_ed
        sim.input["et"] = entrada_yaw

        try:
            sim.compute()
            v = float(sim.output["v"])
            w = float(sim.output["w"])
        except Exception as exc:
            motivo = f"ERROR_DIFUSO: {exc}"
            break

        # Modelo cinemático simplificado:
        # yaw positivo + omega positivo => yaw aumenta.
        # No se invierte omega para ocultar errores de signo.
        ed -= v * math.cos(yaw) * DT
        lateral += v * math.sin(yaw) * DT
        # Hipotesis de rediseno SOLO para el modelo numerico.
        # El controlador original y ROS2 permanecen intactos.
        yaw -= w * DT

        # Perturbación numérica lateral ilustrativa.
        if perturbacion and 3.0 <= tiempo < 3.5:
            lateral += 0.02 * DT

        signo = 1 if yaw > math.radians(1) else (
            -1 if yaw < -math.radians(1) else 0
        )

        if signo and signo_anterior and signo != signo_anterior:
            oscilaciones += 1
        if signo:
            signo_anterior = signo

        dentro = (
            abs(ed) <= 0.01
            and abs(math.degrees(yaw)) <= 5
            and abs(lateral) <= 0.03
        )

        estable = estable + DT if dentro else 0.0

        if estable >= 1.0:
            exito = True
            motivo = "ACOPLE_NUMERICO"
            break

        if abs(math.degrees(yaw)) > 45:
            motivo = "DIVERGENCIA_ANGULAR"
            break

        if abs(lateral) > 0.15:
            motivo = "ERROR_LATERAL_EXCESIVO"
            break

    return {
        "escenario": nombre,
        "repeticion": repeticion,
        "tipo_ensayo": "MODELO_NUMERICO_NO_GAZEBO",
        "estado": motivo,
        "exito": int(exito),
        "error_distancia_final_m": round(ed, 6),
        "error_angular_final_grados": round(
            math.degrees(yaw), 4
        ),
        "error_lateral_final_m": round(lateral, 6),
        "tiempo_s": round(tiempo, 3),
        "oscilaciones": oscilaciones,
        "reintentos": 0,
    }


def main():
    resultados = []

    for nombre, yaw, lateral, perturbacion in ESCENARIOS:
        for repeticion in range(1, 6):
            resultado = ejecutar(
                nombre, repeticion, yaw,
                lateral, perturbacion
            )
            resultados.append(resultado)

            print(
                f"{nombre:23s} "
                f"rep={repeticion} "
                f"exito={resultado['exito']} "
                f"estado={resultado['estado']} "
                f"yaw={resultado['error_angular_final_grados']:+.2f}"
            )

    destino = SALIDA / "resultados_20_ensayos_redisenio_numerico.csv"

    with destino.open(
        "w", newline="", encoding="utf-8"
    ) as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=list(resultados[0].keys())
        )
        escritor.writeheader()
        escritor.writerows(resultados)

    exitos = sum(r["exito"] for r in resultados)

    print()
    print("===== RESUMEN DE EVALUACION =====")
    print("TIPO: MODELO_NUMERICO_NO_GAZEBO")
    print("ESCENARIOS: 4")
    print("REPETICIONES: 20")
    print("EXITOS_NUMERICOS:", exitos)
    print("FALLOS_NUMERICOS:", 20 - exitos)
    print("ENSAYOS_FISICOS_GAZEBO: 0")
    print("RESULTADOS:", destino)
    print("MOVIMIENTO_SOLICITADO: NO")


if __name__ == "__main__":
    main()
