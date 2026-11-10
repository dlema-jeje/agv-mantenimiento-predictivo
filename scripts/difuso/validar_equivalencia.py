
#!/usr/bin/env python3
"""Comparacion preliminar de un controlador Mamdani en Python."""

from pathlib import Path

import numpy as np
import pandas as pd
import skfuzzy as fuzz
from skfuzzy import control as ctrl

PROYECTO = Path.home() / "agv_predictivo"
RESULTADOS = PROYECTO / "resultados" / "avance2" / "validacion"

# Universos de discurso
ed = ctrl.Antecedent(np.linspace(-0.05, 0.45, 1001), "ed")
et = ctrl.Antecedent(np.linspace(-20, 20, 1001), "et")
v = ctrl.Consequent(np.linspace(-0.05, 0.15, 2001), "v")
w = ctrl.Consequent(np.linspace(-0.8, 0.8, 2001), "w")

# Error de distancia
ed["Pasado"] = fuzz.trapmf(ed.universe, [-0.05, -0.05, -0.03, -0.005])
ed["Acoplado"] = fuzz.trimf(ed.universe, [-0.015, 0, 0.015])
ed["MuyCerca"] = fuzz.trimf(ed.universe, [0.005, 0.04, 0.09])
ed["Cerca"] = fuzz.trimf(ed.universe, [0.06, 0.15, 0.28])
ed["Lejos"] = fuzz.trapmf(ed.universe, [0.22, 0.32, 0.45, 0.45])

# Error angular
et["NegGrande"] = fuzz.trapmf(et.universe, [-20, -20, -15, -8])
et["NegPequeno"] = fuzz.trimf(et.universe, [-15, -7, 0])
et["Cero"] = fuzz.trimf(et.universe, [-5, 0, 5])
et["PosPequeno"] = fuzz.trimf(et.universe, [0, 7, 15])
et["PosGrande"] = fuzz.trapmf(et.universe, [8, 15, 20, 20])

# Velocidad lineal
v["Retroceso"] = fuzz.trapmf(v.universe, [-0.05, -0.05, -0.035, -0.005])
v["Cero"] = fuzz.trimf(v.universe, [-0.01, 0, 0.01])
v["MuyLenta"] = fuzz.trimf(v.universe, [0.005, 0.025, 0.05])
v["Lenta"] = fuzz.trimf(v.universe, [0.035, 0.07, 0.105])
v["Media"] = fuzz.trapmf(v.universe, [0.09, 0.12, 0.15, 0.15])

# Velocidad angular
w["NegGrande"] = fuzz.trapmf(w.universe, [-0.8, -0.8, -0.65, -0.3])
w["NegMedia"] = fuzz.trimf(w.universe, [-0.55, -0.3, 0])
w["Cero"] = fuzz.trimf(w.universe, [-0.1, 0, 0.1])
w["PosMedia"] = fuzz.trimf(w.universe, [0, 0.3, 0.55])
w["PosGrande"] = fuzz.trapmf(w.universe, [0.3, 0.65, 0.8, 0.8])

# Matriz de decisiones: filas distancia, columnas angulo
distancias = ["Pasado", "Acoplado", "MuyCerca", "Cerca", "Lejos"]
angulos = ["NegGrande", "NegPequeno", "Cero", "PosPequeno", "PosGrande"]
lineales = ["Retroceso", "Cero", "MuyLenta", "Lenta", "Media"]
angulares = ["NegGrande", "NegMedia", "Cero", "PosMedia", "PosGrande"]

tabla_lineal = [
    [1, 1, 1, 1, 1],
    [2, 2, 2, 2, 2],
    [2, 3, 3, 3, 2],
    [3, 4, 4, 4, 3],
    [3, 4, 5, 4, 3],
]

reglas = []

for i, nombre_distancia in enumerate(distancias):
    for j, nombre_angulo in enumerate(angulos):
        nombre_lineal = lineales[tabla_lineal[i][j] - 1]
        nombre_angular = angulares[j]

        reglas.append(
            ctrl.Rule(
                ed[nombre_distancia] & et[nombre_angulo],
                (v[nombre_lineal], w[nombre_angular]),
            )
        )

sistema = ctrl.ControlSystem(reglas)

pruebas = [
    (0.35, 0),
    (0.15, 0),
    (0.04, 0),
    (0.00, 0),
    (-0.03, 0),
    (0.15, 12),
    (0.15, -12),
    (0.04, 18),
    (0.04, -18),
    (0.00, 3),
]

filas = []

for numero, (error_distancia, error_angular) in enumerate(pruebas, 1):
    simulacion = ctrl.ControlSystemSimulation(sistema)
    simulacion.input["ed"] = error_distancia
    simulacion.input["et"] = error_angular
    simulacion.compute()

    filas.append(
        {
            "Caso": numero,
            "ErrorDistancia_m": error_distancia,
            "ErrorAngular_deg": error_angular,
            "VelocidadLineal_m_s": simulacion.output["v"],
            "VelocidadAngular_rad_s": simulacion.output["w"],
        }
    )

tabla = pd.DataFrame(filas)
RESULTADOS.mkdir(parents=True, exist_ok=True)

ruta = RESULTADOS / "pruebas_controlador_python.csv"
tabla.to_csv(ruta, index=False)

print("\n===== RESULTADOS PYTHON =====")
print(tabla.to_string(index=False))
print(f"\nReglas implementadas: {len(reglas)}")
print(f"Archivo guardado: {ruta}")
