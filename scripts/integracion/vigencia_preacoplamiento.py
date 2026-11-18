#!/usr/bin/env python3
"""Validacion temporal conservadora para el preacoplamiento."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenciaTemporal:
    valida: bool
    motivo: str


def verificar_vigencia(
    *,
    ahora,
    t_nav2,
    t_arbitro,
    t_odom,
    t_sensores,
    estado_nav2,
    estado_arbitro,
    max_edad=0.5,
):
    """Rechaza evidencias ausentes, futuras, obsoletas o invalidas."""

    valores = (ahora, t_nav2, t_arbitro, t_odom, t_sensores, max_edad)

    if any(
        isinstance(v, bool)
        or not isinstance(v, (int, float))
        or not math.isfinite(v)
        for v in valores
    ):
        return EvidenciaTemporal(False, "TIEMPOS_INVALIDOS")

    if ahora <= 0 or max_edad <= 0:
        return EvidenciaTemporal(False, "PARAMETROS_TEMPORALES_INVALIDOS")

    evidencias = (
        ("NAV2", t_nav2),
        ("ARBITRO", t_arbitro),
        ("ODOMETRIA", t_odom),
        ("SENSORES", t_sensores),
    )

    for nombre, instante in evidencias:
        if instante <= 0:
            return EvidenciaTemporal(False, f"{nombre}_SIN_EVIDENCIA")

        edad = ahora - instante

        if edad < 0:
            return EvidenciaTemporal(False, f"{nombre}_TIEMPO_FUTURO")

        if edad > max_edad:
            return EvidenciaTemporal(False, f"{nombre}_OBSOLETO")

    if estado_nav2 != "FINALIZADO":
        return EvidenciaTemporal(False, "NAV2_NO_FINALIZADO")

    if estado_arbitro != "STOP":
        return EvidenciaTemporal(False, "ARBITRO_NO_STOP")

    return EvidenciaTemporal(True, "EVIDENCIAS_VIGENTES")
