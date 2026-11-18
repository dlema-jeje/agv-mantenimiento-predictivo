#!/usr/bin/env python3
"""Validacion conservadora de finalizacion Nav2, sin efectos ROS."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ValidacionFinal:
    autorizado: bool
    estado: str
    motivo: str


def validar_finalizacion_nav2(
    *,
    exito_nav2,
    cancelacion_solicitada,
    stop_confirmado,
    velocidad_lineal,
    velocidad_angular,
    antiguedad_odom,
):
    """Solo confirma finalizacion con todas las evidencias validas."""

    if exito_nav2 is not True:
        return ValidacionFinal(
            False, "NO_CONFIRMADO", "NAV2_SIN_EXITO_CONFIRMADO"
        )

    if cancelacion_solicitada is not False:
        return ValidacionFinal(
            False, "NO_CONFIRMADO", "CANCELACION_O_ESTADO_INCIERTO"
        )

    if stop_confirmado is not True:
        return ValidacionFinal(
            False, "NO_CONFIRMADO", "STOP_NO_CONFIRMADO"
        )

    valores = (
        velocidad_lineal,
        velocidad_angular,
        antiguedad_odom,
    )

    if any(
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
        or not math.isfinite(valor)
        for valor in valores
    ):
        return ValidacionFinal(
            False, "NO_CONFIRMADO", "ODOMETRIA_INVALIDA"
        )

    if not 0 <= antiguedad_odom < 0.3:
        return ValidacionFinal(
            False, "NO_CONFIRMADO", "ODOMETRIA_OBSOLETA"
        )

    if (
        abs(velocidad_lineal) >= 0.01
        or abs(velocidad_angular) >= 0.03
    ):
        return ValidacionFinal(
            False, "NO_CONFIRMADO", "ROBOT_NO_DETENIDO"
        )

    return ValidacionFinal(
        True, "FINALIZADO", "NAV2_Y_PARADA_CONFIRMADOS"
    )
