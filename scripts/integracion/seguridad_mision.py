#!/usr/bin/env python3
"""Comprobaciones de seguridad y registro de incidencias."""

import csv
import math
import time
from datetime import datetime
from pathlib import Path

from nav_msgs.msg import Odometry


def odometria_detenida(odom, recibido, antiguedad_maxima=0.5):
    if odom is None or time.monotonic() - recibido > antiguedad_maxima:
        return False

    v = odom.twist.twist.linear.x
    w = odom.twist.twist.angular.z

    return (
        math.isfinite(v)
        and math.isfinite(w)
        and abs(v) < 0.01
        and abs(w) < 0.03
    )


def registrar_incidencia(estacion, evento, detalle, archivo=None):
    if archivo is None:
        archivo = (
            "datos/registros/integracion/"
            "incidencias_nav2.csv"
        )

    ruta = Path(archivo)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    registro = {
        "fecha": datetime.now().isoformat(),
        "estacion": estacion,
        "evento": evento,
        "detalle": detalle,
    }

    existe = ruta.exists() and ruta.stat().st_size > 0

    with ruta.open("a", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=registro.keys())
        if not existe:
            escritor.writeheader()
        escritor.writerow(registro)

    return registro
