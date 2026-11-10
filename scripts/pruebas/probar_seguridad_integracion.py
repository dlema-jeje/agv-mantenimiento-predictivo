#!/usr/bin/env python3
"""Pruebas aisladas de lógica de misión; no crea nodos ROS."""

import csv
import sys
import time
from datetime import datetime
from pathlib import Path

from action_msgs.msg import GoalStatus
from nav_msgs.msg import Odometry

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "integracion")
)

from seguridad_mision import (
    odometria_detenida,
    registrar_incidencia,
)
from registro_resultados_nav2 import interpretar_resultado


def decision_final(estado, cancelacion_confirmada, stop, odom_ok):
    """Decisión conservadora ante respuestas simuladas."""
    if not stop or not odom_ok:
        return "PARADA_NO_VERIFICADA"

    if estado == GoalStatus.STATUS_SUCCEEDED:
        return "NAV2_FINALIZADO"

    if estado == GoalStatus.STATUS_CANCELED:
        if cancelacion_confirmada:
            return "CANCELACION_CONFIRMADA"
        return "CANCELACION_NO_CONFIRMADA"

    if estado == GoalStatus.STATUS_ABORTED:
        return "NAV2_ABORTADO"

    return "RESULTADO_NO_CONFIRMADO"


def crear_odom(v=0.0, w=0.0):
    odom = Odometry()
    odom.twist.twist.linear.x = v
    odom.twist.twist.angular.z = w
    return odom


def main():
    ahora = time.monotonic()

    casos = [
        (
            "EXITO_CON_PARADA",
            GoalStatus.STATUS_SUCCEEDED,
            True, True,
            crear_odom(),
            ahora,
            "NAV2_FINALIZADO",
        ),
        (
            "CANCELACION_CONFIRMADA",
            GoalStatus.STATUS_CANCELED,
            True, True,
            crear_odom(),
            ahora,
            "CANCELACION_CONFIRMADA",
        ),
        (
            "CANCELACION_NO_CONFIRMADA",
            GoalStatus.STATUS_CANCELED,
            False, True,
            crear_odom(),
            ahora,
            "CANCELACION_NO_CONFIRMADA",
        ),
        (
            "NAVEGACION_ABORTADA",
            GoalStatus.STATUS_ABORTED,
            False, True,
            crear_odom(),
            ahora,
            "NAV2_ABORTADO",
        ),
        (
            "ROBOT_EN_MOVIMIENTO",
            GoalStatus.STATUS_SUCCEEDED,
            True, True,
            crear_odom(v=0.05),
            ahora,
            "PARADA_NO_VERIFICADA",
        ),
        (
            "ODOMETRIA_OBSOLETA",
            GoalStatus.STATUS_SUCCEEDED,
            True, True,
            crear_odom(),
            ahora - 2.0,
            "PARADA_NO_VERIFICADA",
        ),
        (
            "STOP_NO_CONFIRMADO",
            GoalStatus.STATUS_SUCCEEDED,
            True, False,
            crear_odom(),
            ahora,
            "PARADA_NO_VERIFICADA",
        ),
        (
            "ESTADO_DESCONOCIDO",
            GoalStatus.STATUS_UNKNOWN,
            False, True,
            crear_odom(),
            ahora,
            "RESULTADO_NO_CONFIRMADO",
        ),
    ]

    resultados = []

    for nombre, estado, cancelada, stop, odom, t_odom, esperado in casos:
        odom_ok = odometria_detenida(odom, t_odom)

        obtenido = decision_final(
            estado,
            cancelada,
            stop,
            odom_ok,
        )

        aprobado = obtenido == esperado

        resultados.append({
            "fecha": datetime.now().isoformat(),
            "caso": nombre,
            "estado_nav2_simulado": interpretar_resultado(estado),
            "cancelacion_confirmada_simulada": cancelada,
            "stop_confirmado_simulado": stop,
            "odometria_detenida": odom_ok,
            "resultado_esperado": esperado,
            "resultado_obtenido": obtenido,
            "prueba_aprobada": aprobado,
            "tipo": "SIMULACION_LOGICA",
        })

        print(
            f"{nombre}: "
            f"{'APROBADA' if aprobado else 'FALLIDA'} "
            f"({obtenido})"
        )

    ruta = Path(
        "datos/registros/integracion/"
        "pruebas_seguridad_mision.csv"
    )

    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=resultados[0].keys(),
        )
        escritor.writeheader()
        escritor.writerows(resultados)

    fallidas = sum(
        not fila["prueba_aprobada"] for fila in resultados
    )

    if fallidas:
        registrar_incidencia(
            "BANCO_PRUEBAS",
            "PRUEBAS_FALLIDAS",
            f"{fallidas} casos fallidos",
        )

    print()
    print(f"PRUEBAS_TOTALES: {len(resultados)}")
    print(f"PRUEBAS_APROBADAS: {len(resultados) - fallidas}")
    print(f"PRUEBAS_FALLIDAS: {fallidas}")
    print(f"REGISTRO_GENERADO: {ruta}")
    print("OBJETIVOS_NAV2_ENVIADOS: 0")
    print("MOVIMIENTO_SOLICITADO: NO")

    if fallidas:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
