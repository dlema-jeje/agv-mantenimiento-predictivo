#!/usr/bin/env python3
"""Validacion conservadora del preacoplamiento, sin ROS."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoPreacoplamiento:
    confirmado: bool
    estado: str
    motivo: str


def validar_preacoplamiento(
    *,
    geometria_apta,
    nav2_finalizado,
    robot_detenido,
    sensores_validos,
):
    """La ausencia de cualquier evidencia impide confirmar la pose."""

    condiciones = (
        ("GEOMETRIA_NO_CONFIRMADA", geometria_apta),
        ("NAV2_NO_FINALIZADO", nav2_finalizado),
        ("PARADA_NO_CONFIRMADA", robot_detenido),
        ("SENSORES_NO_VALIDOS", sensores_validos),
    )

    for motivo, valor in condiciones:
        if valor is not True:
            return ResultadoPreacoplamiento(
                confirmado=False,
                estado="NO_CONFIRMADO",
                motivo=motivo,
            )

    return ResultadoPreacoplamiento(
        confirmado=True,
        estado="POSE_APTA",
        motivo="PREACOPLAMIENTO_VERIFICADO",
    )
