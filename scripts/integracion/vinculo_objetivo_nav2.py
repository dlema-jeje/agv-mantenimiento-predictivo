#!/usr/bin/env python3
"""Vínculo verificable entre una misión y su objetivo Nav2.

Módulo independiente de ROS 2. No envía objetivos ni velocidades.
"""

import csv
import math
from dataclasses import dataclass
from pathlib import Path


ESTACIONES = frozenset(("E1", "E2", "E3", "E4", "E5"))


@dataclass(frozen=True)
class VinculoObjetivo:
    valido: bool
    estacion: str
    mision_id: str
    motivo: str


def cargar_aproximacion(estacion, archivo=None):
    if estacion not in ESTACIONES:
        raise ValueError("ESTACION_INVALIDA")

    if archivo is None:
        archivo = (
            Path(__file__).resolve().parents[2]
            / "datos"
            / "objetivos_acoplamiento.csv"
        )

    with open(archivo, newline="", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))

    coincidencias = [
        fila for fila in filas
        if fila.get("estacion") == estacion
    ]

    if len(coincidencias) != 1:
        raise ValueError("ESTACION_NO_UNICA_O_AUSENTE")

    fila = coincidencias[0]

    return (
        float(fila["pre_x"]),
        float(fila["pre_y"]),
        math.radians(float(fila["pre_yaw"])),
    )


def verificar_objetivo(
    *,
    estacion,
    mision_id,
    objetivo_x,
    objetivo_y,
    objetivo_yaw_rad,
    tolerancia_posicion=0.001,
    tolerancia_angular=math.radians(0.1),
):
    if estacion not in ESTACIONES:
        return VinculoObjetivo(
            False, estacion, mision_id, "ESTACION_INVALIDA"
        )

    if not isinstance(mision_id, str) or not mision_id:
        return VinculoObjetivo(
            False, estacion, mision_id, "MISION_INVALIDA"
        )

    valores = (
        objetivo_x,
        objetivo_y,
        objetivo_yaw_rad,
        tolerancia_posicion,
        tolerancia_angular,
    )

    if not all(
        isinstance(v, (int, float))
        and not isinstance(v, bool)
        and math.isfinite(v)
        for v in valores
    ):
        return VinculoObjetivo(
            False, estacion, mision_id, "VALORES_INVALIDOS"
        )

    if tolerancia_posicion < 0 or tolerancia_angular < 0:
        return VinculoObjetivo(
            False, estacion, mision_id, "TOLERANCIA_INVALIDA"
        )

    try:
        esperado_x, esperado_y, esperado_yaw = (
            cargar_aproximacion(estacion)
        )
    except (OSError, ValueError, KeyError):
        return VinculoObjetivo(
            False, estacion, mision_id, "OBJETIVO_NO_DISPONIBLE"
        )

    distancia = math.hypot(
        objetivo_x - esperado_x,
        objetivo_y - esperado_y,
    )

    diferencia_yaw = math.atan2(
        math.sin(objetivo_yaw_rad - esperado_yaw),
        math.cos(objetivo_yaw_rad - esperado_yaw),
    )

    if distancia > tolerancia_posicion:
        return VinculoObjetivo(
            False, estacion, mision_id, "POSICION_NO_COINCIDE"
        )

    if abs(diferencia_yaw) > tolerancia_angular:
        return VinculoObjetivo(
            False, estacion, mision_id, "ORIENTACION_NO_COINCIDE"
        )

    return VinculoObjetivo(
        True, estacion, mision_id, "OBJETIVO_COINCIDENTE"
    )
