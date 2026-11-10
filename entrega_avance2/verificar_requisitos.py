from pathlib import Path
import importlib.util
import shutil

raiz = Path.cwd()

print("\n===== CONTROL DIFUSO =====")
for nombre in [
    "scripts/difuso/controlador_agv.py",
    "scripts/difuso/supervisor_geometrico.py",
    "scripts/difuso/nodo_acoplamiento_ros2.py",
    "scripts/integracion/cliente_nav2_supervisado.py",
]:
    ruta = raiz / nombre
    print(f"{'OK' if ruta.is_file() else 'FALTA'}: {nombre}")

print("\n===== ARCHIVOS MATLAB / FIS =====")
archivos = []
for extension in ("*.fis", "*.m"):
    archivos.extend(raiz.rglob(extension))

for ruta in archivos[:30]:
    print(ruta.relative_to(raiz))
print("TOTAL_MATLAB_FIS:", len(archivos))

print("\n===== DATASET DE VIBRACION =====")
datos = []
for extension in ("*.mat", "*.csv", "*.npy", "*.npz"):
    for ruta in raiz.rglob(extension):
        if any(p in ruta.parts for p in (
            ".venv-avance2", ".git", "node_modules"
        )):
            continue
        if ruta.stat().st_size > 100_000:
            datos.append(ruta)

for ruta in datos[:40]:
    print(
        ruta.relative_to(raiz),
        f"({ruta.stat().st_size / 1048576:.2f} MB)"
    )
print("ARCHIVOS_DE_DATOS:", len(datos))

print("\n===== LIBRERIAS =====")
for modulo in [
    "numpy", "scipy", "skfuzzy",
    "sklearn", "tensorflow", "matplotlib",
    "pandas",
]:
    print(
        modulo,
        "OK" if importlib.util.find_spec(modulo)
        else "NO_INSTALADO"
    )

print("\n===== MATLAB / OCTAVE =====")
for programa in ["matlab", "octave"]:
    print(programa, shutil.which(programa) or "NO_EN_PATH")

print("\n===== EVIDENCIAS EXISTENTES =====")
for nombre in [
    "datos/registros/integracion/pruebas_seguridad_mision.csv",
    "datos/registros/integracion/pruebas_acciones_ros2.csv",
    "datos/registros/integracion/resultados_nav2.csv",
    "datos/registros/acoplamientos.csv",
]:
    ruta = raiz / nombre
    print(f"{'OK' if ruta.is_file() else 'FALTA'}: {nombre}")

print("\nDIRECTORIO_ENTREGA:", raiz / "entrega_avance2")
print("MOVIMIENTO_SOLICITADO: NO")
