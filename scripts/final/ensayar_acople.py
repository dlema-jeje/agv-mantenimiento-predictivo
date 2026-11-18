"""Ejecuta cinco intentos independientes por escenario de acople en Gazebo."""
import argparse
import math
from pathlib import Path
import subprocess

import rclpy

from inspeccionar import Inspector, SecuenciaAcoplamiento, angulo

ESCENARIOS = (("frontal", 0., 0.), ("desalineacion_15", 15., 0.),
              ("error_supervisor", 10., 0.03))


def ensayar(nodo):
    nodo.offset_x = 0.
    nodo.esperar(lambda: nodo.odom is not None, 40, "No se recibió odometría del Waffle.")
    eje_y = nodo.objetivos["E1"]
    x = 0.76  # Punto de traspaso del supervisor empleado por Avance 3.
    for nombre, grados, lateral in ESCENARIOS:
        y, yaw = eje_y + lateral, math.radians(grados)
        for repeticion in range(1, 6):
            nodo.mover()
            nodo.rangos.clear()
            subprocess.run(["gz", "model", "-m", "agv_waffle", "-x", str(x), "-y", str(y),
                            "-z", "0.05", "-R", "0", "-P", "0", "-Y", str(yaw)],
                           check=True, timeout=10)
            inicio = nodo.odom[4]
            nodo.esperar(lambda: nodo.odom[4] > inicio + 1.0
                         and math.hypot(nodo.odom[0]-x, nodo.odom[1]-y) < 0.015
                         and abs(angulo(nodo.odom[2]-yaw)) < math.radians(2),
                         8, f"No se confirmó la pose inicial de {nombre}.")
            pose = nodo.pose()
            secuencia = SecuenciaAcoplamiento(max_reintentos=0)
            secuencia.iniciar(True)
            # Límite explícito en segundos simulados para comparar repeticiones.
            metricas, motivo = nodo.intento_acople(secuencia, eje_y, limite_sim=60)
            nodo.guardar({"tipo": "ensayo", "escenario": nombre, "repeticion": repeticion,
                          "pose_inicial": pose, "pose_final": nodo.pose(), "exito": metricas is not None,
                          "motivo": motivo, **(metricas or {})})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registro", type=Path, required=True)
    args = parser.parse_args()
    args.registro.parent.mkdir(parents=True, exist_ok=True)
    args.registro.touch(exist_ok=False)
    rclpy.init()
    nodo = Inspector(args.registro)
    try:
        ensayar(nodo)
    finally:
        if rclpy.ok():
            nodo.mover()
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
