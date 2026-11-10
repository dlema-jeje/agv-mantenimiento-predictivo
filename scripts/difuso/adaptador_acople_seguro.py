#!/usr/bin/env python3
"""Adaptador lógico sin ROS2 ni publicación de velocidades."""

from dataclasses import dataclass
import math

from maquina_estados_acople import Estado, MaquinaEstadosAcople


@dataclass(frozen=True)
class ResultadoControl:
    estado: str
    motivo: str
    v: float
    w: float
    autorizar_publicacion: bool


class AdaptadorAcopleSeguro:
    def __init__(self):
        self.maquina = MaquinaEstadosAcople(
            max_reintentos=2,
            tiempo_estable=1.0,
            tolerancia_ed=0.01,
            tolerancia_et_deg=5.0,
        )

    def _resultado(self, decision, v=0.0, w=0.0):
        permitido = (
            decision.estado == Estado.ACOPLE_DIFUSO
            and decision.permitir_mamdani
        )

        return ResultadoControl(
            estado=decision.estado.value,
            motivo=decision.motivo,
            v=v if permitido else 0.0,
            w=w if permitido else 0.0,
            autorizar_publicacion=False,  # Bloqueo obligatorio.
        )

    def autorizar(
        self, *, pose_apta, robot_detenido,
        sensores_validos, ahora
    ):
        decision = self.maquina.autorizar_preacople(
            pose_apta=pose_apta,
            robot_detenido=robot_detenido,
            sensores_validos=sensores_validos,
            ahora=ahora,
        )
        return self._resultado(decision)

    def actualizar(
        self, *, ed, et_deg, sensores_validos,
        seguridad_apta, v, w, ahora
    ):
        # Una salida difusa inválida nunca puede autorizarse.
        salidas_validas = (
            math.isfinite(v) and math.isfinite(w)
            and -0.05 <= v <= 0.15
            and -0.8 <= w <= 0.8
        )

        if not salidas_validas:
            seguridad_apta = False
            v = 0.0
            w = 0.0

        decision = self.maquina.actualizar_acople(
            ed=ed,
            et_deg=et_deg,
            sensores_validos=sensores_validos,
            seguridad_apta=seguridad_apta,
            ahora=ahora,
        )

        return self._resultado(decision, v, w)
