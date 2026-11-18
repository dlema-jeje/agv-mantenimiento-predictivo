#!/usr/bin/env python3
"""Evaluador de preacoplamiento independiente de ROS 2."""

import math
import sys
from pathlib import Path

RUTA_DIFUSO = str(Path(__file__).resolve().parents[1] / "difuso")
if RUTA_DIFUSO not in sys.path:
    sys.path.insert(0, RUTA_DIFUSO)

from supervisor_geometrico import calcular_errores, evaluar_preacople
from validacion_preacoplamiento import validar_preacoplamiento
from vigencia_preacoplamiento import verificar_vigencia


def evaluar_pose_preacoplamiento(
    *,
    x, y, yaw,
    objetivo_x, objetivo_y, objetivo_yaw,
    nav2_finalizado,
    robot_detenido,
    sensores_validos,
):
    """Evalúa geometría y condiciones de seguridad.

    No autoriza movimiento ni publica comandos.
    """
    coordenadas = (
        x, y, yaw,
        objetivo_x, objetivo_y, objetivo_yaw,
    )

    if any(
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
        or not math.isfinite(valor)
        for valor in coordenadas
    ):
        resultado = validar_preacoplamiento(
            geometria_apta=False,
            nav2_finalizado=nav2_finalizado,
            robot_detenido=robot_detenido,
            sensores_validos=sensores_validos,
        )
        return resultado, None, "COORDENADAS_INVALIDAS"

    errores = calcular_errores(
        x, y, yaw,
        objetivo_x, objetivo_y, objetivo_yaw,
    )

    geometria_apta, motivo_geometrico = evaluar_preacople(errores)

    resultado = validar_preacoplamiento(
        geometria_apta=geometria_apta,
        nav2_finalizado=nav2_finalizado,
        robot_detenido=robot_detenido,
        sensores_validos=sensores_validos,
    )

    return resultado, errores, motivo_geometrico



def evaluar_pose_preacoplamiento_con_vigencia(
    *,
    x, y, yaw,
    objetivo_x, objetivo_y, objetivo_yaw,
    ahora,
    t_nav2,
    t_arbitro,
    t_odom,
    t_sensores,
    estado_nav2,
    estado_arbitro,
    sensores_validos,
    robot_detenido,
    max_edad=0.5,
):
    """Integra evidencias temporales y geometria sin autorizar movimiento."""

    vigencia = verificar_vigencia(
        ahora=ahora,
        t_nav2=t_nav2,
        t_arbitro=t_arbitro,
        t_odom=t_odom,
        t_sensores=t_sensores,
        estado_nav2=estado_nav2,
        estado_arbitro=estado_arbitro,
        max_edad=max_edad,
    )

    resultado, errores, motivo_geometrico = evaluar_pose_preacoplamiento(
        x=x,
        y=y,
        yaw=yaw,
        objetivo_x=objetivo_x,
        objetivo_y=objetivo_y,
        objetivo_yaw=objetivo_yaw,
        nav2_finalizado=(
            vigencia.valida is True
            and estado_nav2 == "FINALIZADO"
        ),
        robot_detenido=(
            vigencia.valida is True
            and robot_detenido is True
            and estado_arbitro == "STOP"
        ),
        sensores_validos=(
            vigencia.valida is True
            and sensores_validos is True
        ),
    )

    return resultado, errores, motivo_geometrico, vigencia
