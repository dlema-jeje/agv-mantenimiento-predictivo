"""Audita un registro JSONL de la misión final en Gazebo."""
import argparse
import json
from pathlib import Path
from statistics import mean

from rondas import ASIGNACIONES, BancoPrueba, ROOT, Rondas


def validar(registro):
    eventos = [json.loads(linea) for linea in registro.read_text().splitlines()]
    planes = [e for e in eventos if e["tipo"] == "plan"]
    visitas = [e for e in eventos if e["tipo"] == "visita"]
    errores = [e["motivo"] for e in eventos if e["tipo"] == "interrupcion"]
    if errores or len(planes) != 3 or len(visitas) != 15:
        raise ValueError(f"Corrida incompleta: {len(planes)} planes, {len(visitas)} visitas, {errores}.")
    banco = BancoPrueba(ROOT / "datos/final/ventanas_prueba.npz")
    estado = Rondas()
    primeras = []
    for n, plan in enumerate(planes, 1):
        estado.pendientes = set(estado.estados)
        esperado = estado.plan()
        if plan["ronda"] != n or plan["plan"] != esperado:
            raise ValueError(f"Plan inicial inesperado en ronda {n}.")
        primeras.append(esperado[0]["estacion"])
        for visita in visitas[5 * (n - 1):5 * n]:
            e = estado.plan()[0]["estacion"]
            indice, _ = banco.leer(n, e)
            clase = ASIGNACIONES[n - 1].get(e, "normal")
            if (visita["ronda"], visita["estacion"], visita["ventana"], visita["clase"]) != (
                    n, e, indice, clase):
                raise ValueError(f"Diagnóstico o secuencia incorrecta en ronda {n}, {e}.")
            if not (abs(visita["ed_m"]) <= 0.01 and abs(visita["et_deg"]) <= 5
                    and visita["acople_s"] >= 1 and 0 <= visita["reintentos"] <= 2):
                raise ValueError(f"Acople fuera de criterio en ronda {n}, {e}.")
            estado.actualizar(e, clase)
            if visita["pendientes"] != estado.plan():
                raise ValueError(f"Plan pendiente incorrecto en ronda {n}, {e}.")
    return dict(rondas=len(planes), visitas=len(visitas), primeras=primeras,
                max_ed_m=max(abs(v["ed_m"]) for v in visitas),
                max_et_deg=max(abs(v["et_deg"]) for v in visitas),
                max_lateral_m=max(abs(v["error_lateral_m"]) for v in visitas),
                acople_promedio_s=mean(v["acople_s"] for v in visitas),
                reintentos=sum(v["reintentos"] for v in visitas))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registro", type=Path)
    args = parser.parse_args()
    print(json.dumps(validar(args.registro), indent=2))


if __name__ == "__main__":
    main()
