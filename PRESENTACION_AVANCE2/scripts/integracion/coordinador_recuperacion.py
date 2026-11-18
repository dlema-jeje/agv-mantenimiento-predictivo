#!/usr/bin/env python3
"""Coordinación de retornos Nav2 para recuperación de acoplamiento.

No ejecuta navegación ni publica velocidades.
"""

import uuid
from dataclasses import dataclass

from identidad_mision import ESTACIONES
from secuencia_acoplamiento import SecuenciaAcoplamiento


@dataclass(frozen=True)
class SolicitudRetorno:
    estacion: str
    mision_id: str
    intento: int
    estado: str


class CoordinadorRecuperacion:
    def __init__(self, estacion, secuencia=None):
        if estacion not in ESTACIONES:
            raise ValueError("ESTACION_INVALIDA")

        self.estacion = estacion
        self.secuencia = (
            secuencia
            if secuencia is not None
            else SecuenciaAcoplamiento(
                tiempo_confirmacion=1.0,
                max_reintentos=2,
            )
        )
        self.retorno_pendiente = None

    def solicitar_retorno(self, motivo):
        if self.secuencia.estado != "ACOPLE_DIFUSO":
            raise RuntimeError("ACOPLE_NO_ACTIVO")

        resultado = self.secuencia.solicitar_recuperacion(motivo)

        if resultado.estado != "RECUPERACION":
            self.retorno_pendiente = None
            return None

        solicitud = SolicitudRetorno(
            estacion=self.estacion,
            mision_id=uuid.uuid4().hex,
            intento=resultado.reintentos,
            estado="SOLICITADO",
        )

        self.retorno_pendiente = solicitud
        return solicitud

    def confirmar_retorno(
        self,
        *,
        estacion,
        mision_id,
        nav2_finalizado,
        objetivo_verificado,
        robot_detenido,
    ):
        solicitud = self.retorno_pendiente

        if solicitud is None:
            return self.secuencia.recuperacion_confirmada(False)

        confirmado = (
            estacion == solicitud.estacion
            and mision_id == solicitud.mision_id
            and nav2_finalizado is True
            and objetivo_verificado is True
            and robot_detenido is True
        )

        resultado = self.secuencia.recuperacion_confirmada(
            confirmado
        )

        if confirmado:
            self.retorno_pendiente = None

        return resultado
