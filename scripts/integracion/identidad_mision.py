#!/usr/bin/env python3
"""Identidad de misión para asociar Nav2 con una estación.

No controla el robot ni publica mensajes ROS.
"""

import json
import re
from dataclasses import dataclass


ESTACIONES = frozenset(("E1", "E2", "E3", "E4", "E5"))
ESTADOS = frozenset((
    "NO_CONFIRMADO",
    "OBJETIVO_RECHAZADO",
    "RESULTADO_RECIBIDO_NO_AUTORIZADO",
    "FINALIZADO",
))


@dataclass(frozen=True)
class EvidenciaMision:
    valida: bool
    estacion: str
    mision_id: str
    estado: str
    motivo: str


def crear_evidencia(*, estacion, mision_id, estado):
    if estacion not in ESTACIONES:
        raise ValueError("ESTACION_INVALIDA")

    if not isinstance(mision_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{8,64}", mision_id
    ):
        raise ValueError("IDENTIFICADOR_INVALIDO")

    if estado not in ESTADOS:
        raise ValueError("ESTADO_INVALIDO")

    return json.dumps(
        {
            "estacion": estacion,
            "mision_id": mision_id,
            "estado": estado,
        },
        separators=(",", ":"),
    )


def verificar_evidencia(*, mensaje, estacion_esperada, mision_esperada):
    try:
        datos = json.loads(mensaje)

        if not isinstance(datos, dict):
            raise ValueError("FORMATO_INVALIDO")

        estacion = datos.get("estacion")
        mision_id = datos.get("mision_id")
        estado = datos.get("estado")

        if estacion not in ESTACIONES:
            raise ValueError("ESTACION_INVALIDA")

        if not isinstance(mision_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{8,64}", mision_id
        ):
            raise ValueError("IDENTIFICADOR_INVALIDO")

        if estado not in ESTADOS:
            raise ValueError("ESTADO_INVALIDO")

        if estacion != estacion_esperada:
            raise ValueError("ESTACION_NO_COINCIDE")

        if mision_id != mision_esperada:
            raise ValueError("MISION_NO_COINCIDE")

        if estado != "FINALIZADO":
            raise ValueError("NAV2_NO_FINALIZADO")

        return EvidenciaMision(
            True, estacion, mision_id, estado, "MISION_CONFIRMADA"
        )

    except (ValueError, TypeError, KeyError) as exc:
        return EvidenciaMision(
            False, "", "", "NO_CONFIRMADO", str(exc)
        )


