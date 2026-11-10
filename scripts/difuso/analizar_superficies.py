#!/usr/bin/env python3
"""Analisis de las superficies de control del AGV."""

from pathlib import Path
import sys

import numpy as np
import matplotlib.pyplot as plt

CARPETA_SCRIPT = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA_SCRIPT))

from controlador_agv import crear_simulacion

PROYECTO = Path.home() / "agv_predictivo"
RESULTADOS = PROYECTO / "resultados" / "avance2" / "validacion"
RESULTADOS.mkdir(parents=True, exist_ok=True)

# Intervalos de las entradas
distancias = np.linspace(-0.05, 0.45, 31)
angulos = np.linspace(-20, 20, 31)

D, A = np.meshgrid(distancias, angulos)

V = np.zeros_like(D)
W = np.zeros_like(D)

simulacion = crear_simulacion()

print("Calculando superficies del controlador...")

for i in range(D.shape[0]):
    for j in range(D.shape[1]):
        simulacion.input["ed"] = float(D[i, j])
        simulacion.input["et"] = float(A[i, j])
        simulacion.compute()

        V[i, j] = simulacion.output["v"]
        W[i, j] = simulacion.output["w"]

# Figura de velocidad lineal
fig1 = plt.figure(figsize=(10, 7))
ax1 = fig1.add_subplot(111, projection="3d")

superficie1 = ax1.plot_surface(
    D, A, V,
    cmap="viridis",
    edgecolor="none"
)

ax1.set_title("Superficie de velocidad lineal - AGV")
ax1.set_xlabel("Error de distancia (m)")
ax1.set_ylabel("Error angular (grados)")
ax1.set_zlabel("Velocidad lineal (m/s)")

fig1.colorbar(superficie1, ax=ax1, shrink=0.6)
fig1.tight_layout()

ruta1 = RESULTADOS / "superficie_velocidad_lineal.png"
fig1.savefig(ruta1, dpi=200)
plt.close(fig1)

# Figura de velocidad angular
fig2 = plt.figure(figsize=(10, 7))
ax2 = fig2.add_subplot(111, projection="3d")

superficie2 = ax2.plot_surface(
    D, A, W,
    cmap="coolwarm",
    edgecolor="none"
)

ax2.set_title("Superficie de velocidad angular - AGV")
ax2.set_xlabel("Error de distancia (m)")
ax2.set_ylabel("Error angular (grados)")
ax2.set_zlabel("Velocidad angular (rad/s)")

fig2.colorbar(superficie2, ax=ax2, shrink=0.6)
fig2.tight_layout()

ruta2 = RESULTADOS / "superficie_velocidad_angular.png"
fig2.savefig(ruta2, dpi=200)
plt.close(fig2)

print("\nANALISIS COMPLETADO")
print(f"Evaluaciones: {D.size}")
print(f"Velocidad lineal: {V.min():.5f} a {V.max():.5f} m/s")
print(f"Velocidad angular: {W.min():.5f} a {W.max():.5f} rad/s")
print(f"Figura guardada: {ruta1}")
print(f"Figura guardada: {ruta2}")
