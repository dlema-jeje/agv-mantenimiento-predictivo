"""Escenario de tres rondas y estado compartido por ejecución y verificación."""
import sys
from pathlib import Path

import numpy as np

from caracteristicas import CLASES

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from priorizador_agv import ESTACIONES, leer_matriz, ordenar

ASIGNACIONES = (
    {"E2": "inner_race"},
    {"E5": "ball"},
    {"E5": "outer_race"},
)


class Rondas:
    def __init__(self):
        self.estados = dict(zip(ESTACIONES, (
            ("Media", 3, "Normal"), ("Baja", 2, "Normal"), ("Alta", 8, "Normal"),
            ("Media", 2, "Normal"), ("Baja", 1, "Normal"),
        )))
        self.matriz = leer_matriz(ROOT / "datos/matriz_distancias.csv")
        self.origen = "Base"
        self.pendientes = set(ESTACIONES)

    def plan(self):
        return ordenar(self.estados, self.matriz, self.origen, self.pendientes)

    def actualizar(self, estacion, clase):
        if estacion not in self.pendientes or clase not in CLASES:
            raise ValueError(f"Diagnóstico inesperado: {estacion}, {clase}")
        criticidad, _, _ = self.estados[estacion]
        self.estados[estacion] = criticidad, 0, "Normal" if clase == "normal" else "Falla"
        self.origen = estacion
        self.pendientes.remove(estacion)


class BancoPrueba:
    def __init__(self, archivo):
        with np.load(archivo, allow_pickle=False) as banco:
            self.muestras = banco["muestras"]
            self.clases = banco["clases"]

    def leer(self, ronda, estacion):
        if estacion not in ESTACIONES or not 1 <= ronda <= len(ASIGNACIONES):
            raise ValueError("Ronda o estación fuera del escenario.")
        clase = ASIGNACIONES[ronda - 1].get(estacion, "normal")
        indices = np.flatnonzero(self.clases == clase)
        indice = int(indices[(ronda + ESTACIONES.index(estacion)) % len(indices)])
        return indice, self.muestras[indice]
