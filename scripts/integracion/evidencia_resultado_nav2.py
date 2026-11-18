#!/usr/bin/env python3
"""Evidencia de resultados Nav2 asociada a una misión concreta.

Este módulo no inicia navegación ni publica velocidades.
"""

import uuid

from identidad_mision import crear_evidencia


class RegistroMisionNav2:
    def __init__(self, estacion):
        if estacion not in ("E1", "E2", "E3", "E4", "E5"):
            raise ValueError("ESTACION_INVALIDA")

        self.estacion = estacion
        self.mision_id = uuid.uuid4().hex
        self.finalizada = False

    def evidencia_inicial(self):
        return crear_evidencia(
            estacion=self.estacion,
            mision_id=self.mision_id,
            estado="NO_CONFIRMADO",
        )

    def evidencia_resultado(self, estado):
        if self.finalizada:
            raise RuntimeError("RESULTADO_YA_REGISTRADO")

        if estado not in (
            "FINALIZADO",
            "NO_CONFIRMADO",
            "OBJETIVO_RECHAZADO",
            "RESULTADO_RECIBIDO_NO_AUTORIZADO",
        ):
            raise ValueError("ESTADO_INVALIDO")

        self.finalizada = True

        return crear_evidencia(
            estacion=self.estacion,
            mision_id=self.mision_id,
            estado=estado,
        )
