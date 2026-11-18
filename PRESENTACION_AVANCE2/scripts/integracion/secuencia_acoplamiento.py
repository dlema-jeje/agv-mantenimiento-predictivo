#!/usr/bin/env python3
"""Secuencia de acoplamiento MEC451, independiente de ROS 2.

Solo calcula estados. No publica velocidades ni ejecuta movimientos.
"""

import math
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class EstadoAcoplamiento:
    estado: str
    reintentos: int
    completado: bool
    motivo: str


class SecuenciaAcoplamiento:
    def __init__(self, tiempo_confirmacion=1.0, max_reintentos=2):
        self.tiempo_confirmacion = tiempo_confirmacion
        self.max_reintentos = max_reintentos
        self.reintentos = 0
        self.inicio_tolerancia = None
        self.estado = "ESPERANDO_PREACOPLE"

    def resultado(self, motivo):
        return EstadoAcoplamiento(
            estado=self.estado,
            reintentos=self.reintentos,
            completado=(self.estado == "COMPLETADO"),
            motivo=motivo,
        )

    def iniciar(self, preacoplamiento_confirmado):
        if self.estado != "ESPERANDO_PREACOPLE":
            return self.resultado("ESTADO_NO_DISPONIBLE")

        if preacoplamiento_confirmado is not True:
            return self.resultado("PREACOPLAMIENTO_NO_CONFIRMADO")

        self.estado = "ACOPLE_DIFUSO"
        self.inicio_tolerancia = None
        return self.resultado("PREACOPLAMIENTO_CONFIRMADO")

    def actualizar(
        self,
        *,
        error_distancia,
        error_angular,
        sensores_validos,
        seguridad_confirmada,
        ahora=None,
    ):
        if ahora is None:
            ahora = time.monotonic()

        if self.estado != "ACOPLE_DIFUSO":
            return self.resultado("ACOPLE_NO_ACTIVO")

        valores = (error_distancia, error_angular, ahora)

        datos_validos = all(
            isinstance(valor, (int, float))
            and not isinstance(valor, bool)
            and math.isfinite(valor)
            for valor in valores
        )

        if (
            not datos_validos
            or sensores_validos is not True
            or seguridad_confirmada is not True
        ):
            return self.solicitar_recuperacion("LECTURA_O_SEGURIDAD_INVALIDA")

        dentro_tolerancia = (
            abs(error_distancia) <= 0.01
            and abs(error_angular) <= math.radians(5)
        )

        if not dentro_tolerancia:
            self.inicio_tolerancia = None
            return self.resultado("FUERA_DE_TOLERANCIA")

        if self.inicio_tolerancia is None:
            self.inicio_tolerancia = ahora
            return self.resultado("CONFIRMANDO_TOLERANCIA")

        if ahora < self.inicio_tolerancia:
            self.inicio_tolerancia = None
            return self.solicitar_recuperacion("TIEMPO_INVALIDO")

        if ahora - self.inicio_tolerancia >= self.tiempo_confirmacion:
            self.estado = "COMPLETADO"
            return self.resultado("TOLERANCIA_SOSTENIDA_1_SEGUNDO")

        return self.resultado("CONFIRMANDO_TOLERANCIA")

    def solicitar_recuperacion(self, motivo):
        if self.estado != "ACOPLE_DIFUSO":
            return self.resultado("RECUPERACION_NO_DISPONIBLE")

        self.inicio_tolerancia = None

        if self.reintentos >= self.max_reintentos:
            self.estado = "FALLO"
            return self.resultado("MAXIMO_REINTENTOS_AGOTADO")

        self.reintentos += 1
        self.estado = "RECUPERACION"
        return self.resultado(motivo)

    def recuperacion_confirmada(self, retorno_verificado):
        if self.estado != "RECUPERACION":
            return self.resultado("RECUPERACION_NO_ACTIVA")

        if retorno_verificado is not True:
            return self.resultado("RETORNO_NO_CONFIRMADO")

        self.estado = "ESPERANDO_PREACOPLE"
        return self.resultado("LISTO_PARA_REINTENTAR")
