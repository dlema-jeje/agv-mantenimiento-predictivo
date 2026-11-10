
#!/usr/bin/env python3
"""Comparacion cuantitativa de las salidas Mamdani MATLAB-Python."""

from pathlib import Path

import numpy as np
import pandas as pd

PROYECTO = Path.home() / "agv_predictivo"
CARPETA = PROYECTO / "resultados" / "avance2" / "validacion"

RUTA_MATLAB = CARPETA / "pruebas_controlador_mamdani.csv"
RUTA_PYTHON = CARPETA / "pruebas_controlador_python.csv"

matlab = pd.read_csv(RUTA_MATLAB)
python = pd.read_csv(RUTA_PYTHON)

COLUMNAS = [
    "Caso",
    "ErrorDistancia_m",
    "ErrorAngular_deg",
    "VelocidadLineal_m_s",
    "VelocidadAngular_rad_s",
]

for nombre, tabla in [("MATLAB", matlab), ("Python", python)]:
    faltantes = set(COLUMNAS) - set(tabla.columns)
    if faltantes:
        raise ValueError(
            f"{nombre}: faltan columnas {sorted(faltantes)}"
        )

    if tabla["Caso"].duplicated().any():
        raise ValueError(f"{nombre}: existen casos duplicados")

comparacion = matlab[COLUMNAS].merge(
    python[COLUMNAS],
    on="Caso",
    how="outer",
    suffixes=("_MATLAB", "_Python"),
    validate="one_to_one",
    indicator=True,
)

if not comparacion["_merge"].eq("both").all():
    raise ValueError("MATLAB y Python no contienen los mismos casos")

comparacion = comparacion.drop(columns="_merge").sort_values("Caso")

# Comprobar que ambos programas evaluaron las mismas entradas.
for variable in ["ErrorDistancia_m", "ErrorAngular_deg"]:
    a = comparacion[f"{variable}_MATLAB"].to_numpy()
    b = comparacion[f"{variable}_Python"].to_numpy()

    if not np.allclose(a, b, rtol=0, atol=1e-10):
        raise ValueError(f"Las entradas difieren: {variable}")

# Diferencias absolutas entre las dos implementaciones.
comparacion["ErrorLineal_m_s"] = np.abs(
    comparacion["VelocidadLineal_m_s_MATLAB"]
    - comparacion["VelocidadLineal_m_s_Python"]
)

comparacion["ErrorAngular_rad_s"] = np.abs(
    comparacion["VelocidadAngular_rad_s_MATLAB"]
    - comparacion["VelocidadAngular_rad_s_Python"]
)

error_lineal_max = comparacion["ErrorLineal_m_s"].max()
error_angular_max = comparacion["ErrorAngular_rad_s"].max()

error_lineal_medio = comparacion["ErrorLineal_m_s"].mean()
error_angular_medio = comparacion["ErrorAngular_rad_s"].mean()

# Tolerancias iniciales de comparacion, no criterios
# definitivos de seguridad o rendimiento del AGV.
TOLERANCIA_LINEAL = 0.002
TOLERANCIA_ANGULAR = 0.01

cumple = (
    error_lineal_max <= TOLERANCIA_LINEAL
    and error_angular_max <= TOLERANCIA_ANGULAR
)

salida = CARPETA / "comparacion_matlab_python.csv"
comparacion.to_csv(salida, index=False)

print("\n===== COMPARACION MATLAB - PYTHON =====")
print(
    comparacion[
        ["Caso", "ErrorLineal_m_s", "ErrorAngular_rad_s"]
    ].to_string(index=False)
)

print("\n===== RESUMEN DE ERRORES =====")
print(f"Error lineal maximo:  {error_lineal_max:.8f} m/s")
print(f"Error angular maximo: {error_angular_max:.8f} rad/s")
print(f"Error lineal medio:   {error_lineal_medio:.8f} m/s")
print(f"Error angular medio:  {error_angular_medio:.8f} rad/s")

print("\n===== EVALUACION =====")
print(f"Tolerancia lineal:  {TOLERANCIA_LINEAL} m/s")
print(f"Tolerancia angular: {TOLERANCIA_ANGULAR} rad/s")

if cumple:
    print("RESULTADO: COINCIDENCIA DENTRO DE TOLERANCIAS")
else:
    print("RESULTADO: REVISAR DIFERENCIAS ENTRE IMPLEMENTACIONES")

print(f"\nArchivo guardado: {salida}")
