#!/usr/bin/env python3

import math
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "difuso")
)

from controlador_agv import crear_simulacion
from supervisor_geometrico import (
    calcular_errores,
    evaluar_preacople,
)

# Pose ilustrativa, no medición del robot.
x = 0.948
y = -1.197
yaw = math.radians(-25.66)

# Objetivo virtual 3 cm detrás del AGV.
gx = x - 0.03 * math.cos(yaw)
gy = y - 0.03 * math.sin(yaw)
gyaw = yaw

errores = calcular_errores(
    x, y, yaw, gx, gy, gyaw
)

apto, motivo = evaluar_preacople(errores)

print("===== SUPERVISOR =====")
print("Apto:", apto)
print("Motivo:", motivo)
print("Longitudinal:", round(errores["longitudinal"], 4))
print("Lateral:", round(errores["lateral"], 4))
print("Angular:", round(math.degrees(errores["angular"]), 2))

if not apto:
    raise SystemExit("Prueba rechazada por supervisor.")

sim = crear_simulacion()
sim.input["ed"] = errores["longitudinal"]
sim.input["et"] = math.degrees(errores["angular"])
sim.compute()

v = float(sim.output["v"])
w = float(sim.output["w"])

v_limitada = max(-0.035, min(0.035, v))

print("\n===== CONTROLADOR MAMDANI =====")
print("Velocidad lineal difusa:", round(v, 5), "m/s")
print("Velocidad angular difusa:", round(w, 5), "rad/s")
print("Velocidad lineal limitada:", round(v_limitada, 5), "m/s")
print("Movimiento publicado: NO")
