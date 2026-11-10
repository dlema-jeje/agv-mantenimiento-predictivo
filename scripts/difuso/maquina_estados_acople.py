#!/usr/bin/env python3
"""Máquina de estados del acoplamiento AGV.

No publica comandos ROS2 ni controla motores.
Las decisiones de movimiento corresponden al supervisor externo.
"""

from dataclasses import dataclass
from enum import Enum
import math


class Estado(str, Enum):
    PREACOPLE = "PREACOPLE"
    ACOPLE_DIFUSO = "ACOPLE_DIFUSO"
    RECUPERACION = "RECUPERACION"
    COMPLETADO = "COMPLETADO"
    FALLO = "FALLO"


@dataclass(frozen=True)
class Decision:
    estado: Estado
    motivo: str
    permitir_mamdani: bool
    solicitar_detencion: bool
    solicitar_retorno: bool


class MaquinaEstadosAcople:
    def __init__(
        self,
        max_reintentos=2,
        tiempo_estable=1.0,
        tolerancia_ed=0.01,
        tolerancia_et_deg=5.0,
    ):
        self.estado = Estado.PREACOPLE
        self.max_reintentos = max_reintentos
        self.reintentos = 0
        self.tiempo_estable = tiempo_estable
        self.tolerancia_ed = tolerancia_ed
        self.tolerancia_et_deg = tolerancia_et_deg
        self.inicio_estable = None
        self.ultimo_tiempo = None
        self.motivo = "ESPERANDO_PREACOPLE"

    def _decision(self):
        activo = self.estado == Estado.ACOPLE_DIFUSO
        return Decision(
            estado=self.estado,
            motivo=self.motivo,
            permitir_mamdani=activo,
            solicitar_detencion=not activo,
            solicitar_retorno=self.estado == Estado.RECUPERACION,
        )

    def _actualizar_tiempo(self, ahora):
        if not math.isfinite(ahora):
            raise ValueError("Tiempo no finito")
        if self.ultimo_tiempo is not None and ahora < self.ultimo_tiempo:
            self.estado = Estado.FALLO
            self.motivo = "RELOJ_NO_MONOTONICO"
            self.inicio_estable = None
            return False
        self.ultimo_tiempo = ahora
        return True

    def autorizar_preacople(
        self,
        *,
        pose_apta,
        robot_detenido,
        sensores_validos,
        ahora,
    ):
        if not self._actualizar_tiempo(ahora):
            return self._decision()

        if self.estado != Estado.PREACOPLE:
            return self._decision()

        if not pose_apta:
            self.motivo = "POSE_NO_APTA"
        elif not robot_detenido:
            self.motivo = "ROBOT_NO_DETENIDO"
        elif not sensores_validos:
            self.motivo = "SENSORES_INVALIDOS"
        else:
            self.estado = Estado.ACOPLE_DIFUSO
            self.inicio_estable = None
            self.motivo = "ACOPLE_AUTORIZADO"

        return self._decision()

    def actualizar_acople(
        self,
        *,
        ed,
        et_deg,
        sensores_validos,
        seguridad_apta,
        ahora,
    ):
        if not self._actualizar_tiempo(ahora):
            return self._decision()

        if self.estado != Estado.ACOPLE_DIFUSO:
            return self._decision()

        if not sensores_validos:
            return self._recuperar("PERDIDA_SENSORES")

        if not seguridad_apta:
            return self._recuperar("SEGURIDAD_NO_APTA")

        if not math.isfinite(ed) or not math.isfinite(et_deg):
            return self._recuperar("ERRORES_NO_FINITOS")

        estable = (
            abs(ed) <= self.tolerancia_ed
            and abs(et_deg) <= self.tolerancia_et_deg
        )

        if estable:
            if self.inicio_estable is None:
                self.inicio_estable = ahora

            if ahora - self.inicio_estable >= self.tiempo_estable:
                self.estado = Estado.COMPLETADO
                self.motivo = "ACOPLAMIENTO_COMPLETADO"
            else:
                self.motivo = "ESTABILIZANDO"
        else:
            self.inicio_estable = None
            self.motivo = "REGULANDO"

        return self._decision()

    def _recuperar(self, motivo):
        self.inicio_estable = None
        self.reintentos += 1

        if self.reintentos > self.max_reintentos:
            self.estado = Estado.FALLO
            self.motivo = "REINTENTOS_AGOTADOS"
        else:
            self.estado = Estado.RECUPERACION
            self.motivo = motivo

        return self._decision()

    def retorno_confirmado(self, *, ahora):
        if not self._actualizar_tiempo(ahora):
            return self._decision()

        if self.estado == Estado.RECUPERACION:
            self.estado = Estado.PREACOPLE
            self.motivo = "RETORNO_CONFIRMADO"

        return self._decision()
