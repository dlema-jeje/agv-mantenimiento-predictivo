#!/usr/bin/env python3
"""Comprobaciones geométricas para el acoplamiento del AGV."""

import math


def normalizar(angulo):
    return math.atan2(math.sin(angulo), math.cos(angulo))


def calcular_errores(x, y, yaw, gx, gy, gyaw):
    dx = gx - x
    dy = gy - y

    longitudinal = (
        math.cos(gyaw) * dx +
        math.sin(gyaw) * dy
    )

    lateral = (
        -math.sin(gyaw) * dx +
        math.cos(gyaw) * dy
    )

    angular = normalizar(gyaw - yaw)

    distancia = math.hypot(dx, dy)

    return {
        "longitudinal": longitudinal,
        "lateral": lateral,
        "angular": angular,
        "distancia": distancia,
    }


def evaluar_preacople(errores):
    if abs(errores["lateral"]) > 0.02:
        return False, "ERROR_LATERAL_EXCESIVO"

    if abs(errores["angular"]) > math.radians(10):
        return False, "ERROR_ANGULAR_EXCESIVO"

    if not -0.05 <= errores["longitudinal"] <= 0.45:
        return False, "FUERA_DEL_RANGO_DIFUSO"

    if errores["longitudinal"] < 0:
        return False, "OBJETIVO_SOBREPASADO"

    return True, "PREACOPLE_APTO"


def evaluar_acople(errores):
    posicion_correcta = errores["distancia"] <= 0.01

    orientacion_correcta = (
        abs(errores["angular"]) <= math.radians(5)
    )

    return posicion_correcta and orientacion_correcta
