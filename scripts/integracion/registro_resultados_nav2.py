#!/usr/bin/env python3
"""Registro auditable de resultados de navegación Nav2."""

import csv
from datetime import datetime
from pathlib import Path

from action_msgs.msg import GoalStatus


ESTADOS = {
    GoalStatus.STATUS_UNKNOWN: "DESCONOCIDO",
    GoalStatus.STATUS_ACCEPTED: "ACEPTADO",
    GoalStatus.STATUS_EXECUTING: "EJECUTANDO",
    GoalStatus.STATUS_CANCELING: "CANCELANDO",
    GoalStatus.STATUS_SUCCEEDED: "SUCCEEDED",
    GoalStatus.STATUS_CANCELED: "CANCELADO",
    GoalStatus.STATUS_ABORTED: "ABORTADO",
}


def interpretar_resultado(codigo):
    return ESTADOS.get(codigo, f"CODIGO_{codigo}")


def registrar_resultado(
    estacion,
    objetivo_x,
    objetivo_y,
    objetivo_yaw,
    codigo_estado,
    archivo="datos/registros/integracion/resultados_nav2.csv",
):
    ruta = Path(archivo)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    registro = {
        "fecha": datetime.now().isoformat(),
        "estacion": estacion,
        "objetivo_x": objetivo_x,
        "objetivo_y": objetivo_y,
        "objetivo_yaw": objetivo_yaw,
        "codigo_estado": codigo_estado,
        "resultado": interpretar_resultado(codigo_estado),
        "exito_confirmado": (
            codigo_estado == GoalStatus.STATUS_SUCCEEDED
        ),
    }

    existe = ruta.exists() and ruta.stat().st_size > 0

    with ruta.open("a", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(
            f, fieldnames=list(registro.keys())
        )
        if not existe:
            escritor.writeheader()
        escritor.writerow(registro)

    return registro
