#!/usr/bin/env python3
"""Diagnóstico geométrico de preacoplamiento, sin movimiento."""

import argparse
import csv
import math
import time
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener


def normalizar(angulo):
    return math.atan2(math.sin(angulo), math.cos(angulo))


def yaw_cuaternion(q):
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    )


class Diagnostico(Node):
    def __init__(self):
        super().__init__("orquestador_diagnostico_agv")
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(
            self.tf_buffer, self
        )

    def posicion(self):
        transformacion = self.tf_buffer.lookup_transform(
            "map",
            "base_link",
            Time(),
            timeout=Duration(seconds=0.5),
        )
        p = transformacion.transform.translation
        q = transformacion.transform.rotation
        return p.x, p.y, yaw_cuaternion(q)


def leer_estaciones(ruta):
    with open(ruta, newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        columnas = {
            "estacion", "pre_x", "pre_y", "pre_yaw",
            "final_x", "final_y", "final_yaw"
        }
        if not columnas.issubset(set(lector.fieldnames or [])):
            raise ValueError("CSV sin columnas requeridas")

        estaciones = list(lector)

    if not estaciones:
        raise ValueError("CSV sin estaciones")

    return estaciones


def evaluar(estacion, posicion):
    x, y, yaw = posicion

    px = float(estacion["pre_x"])
    py = float(estacion["pre_y"])
    pyaw = float(estacion["pre_yaw"])

    dx = px - x
    dy = py - y

    # Error longitudinal y lateral en el marco del objetivo.
    longitudinal = math.cos(pyaw) * dx + math.sin(pyaw) * dy
    lateral = -math.sin(pyaw) * dx + math.cos(pyaw) * dy
    angular = normalizar(pyaw - yaw)

    # Límites del supervisor geométrico existente.
    geometria_valida = (
        -0.05 <= longitudinal <= 0.45
        and abs(lateral) <= 0.02
        and abs(angular) <= math.radians(10)
    )

    return {
        "error_longitudinal_m": longitudinal,
        "error_lateral_m": lateral,
        "error_angular_deg": math.degrees(angular),
        "geometria_valida": geometria_valida,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--objetivos",
        default="datos/objetivos_acoplamiento.csv"
    )
    parser.add_argument(
        "--salida",
        default="datos/registros/integracion/"
                "diagnostico_cinco_estaciones.csv"
    )
    args = parser.parse_args()

    estaciones = leer_estaciones(args.objetivos)

    rclpy.init()
    nodo = Diagnostico()

    try:
        # Esperar brevemente la disponibilidad de TF2.
        posicion = None
        for _ in range(30):
            rclpy.spin_once(nodo, timeout_sec=0.2)
            try:
                posicion = nodo.posicion()
                break
            except Exception:
                time.sleep(0.1)

        if posicion is None:
            raise RuntimeError(
                "No se obtuvo TF map -> base_link"
            )

        registros = []

        for estacion in estaciones:
            resultado = evaluar(estacion, posicion)

            # La geometría por sí sola NO autoriza acoplamiento.
            registro = {
                "fecha": datetime.now().isoformat(),
                "estacion": estacion["estacion"],
                "robot_x": posicion[0],
                "robot_y": posicion[1],
                "robot_yaw": posicion[2],
                "pre_x": estacion["pre_x"],
                "pre_y": estacion["pre_y"],
                "pre_yaw": estacion["pre_yaw"],
                **resultado,
                "nav2_succeeded": False,
                "autorizacion_mamdani": False,
                "estado": "SOLO_DIAGNOSTICO",
            }
            registros.append(registro)

            print(
                f"{estacion['estacion']}: "
                f"long={resultado['error_longitudinal_m']:.3f} m, "
                f"lat={resultado['error_lateral_m']:.3f} m, "
                f"yaw={resultado['error_angular_deg']:.2f}°, "
                f"geometria={resultado['geometria_valida']}, "
                f"MAMDANI=BLOQUEADO"
            )

        salida = Path(args.salida)
        salida.parent.mkdir(parents=True, exist_ok=True)

        with salida.open(
            "w", newline="", encoding="utf-8"
        ) as archivo:
            escritor = csv.DictWriter(
                archivo,
                fieldnames=list(registros[0].keys())
            )
            escritor.writeheader()
            escritor.writerows(registros)

        print(f"\nREGISTRO_GENERADO: {salida}")
        print(f"ESTACIONES_EVALUADAS: {len(registros)}")
        print("MOVIMIENTO_SOLICITADO: NO")
        print("AUTORIZACION_MAMDANI: NO")

    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
