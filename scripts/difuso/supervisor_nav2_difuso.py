#!/usr/bin/env python3
"""Supervisor de preacople Nav2/difuso. Diagnóstico sin movimiento."""

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import rclpy
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time

from nav2_msgs.action import NavigateToPose
from tf2_ros import Buffer, TransformListener, TransformException

from supervisor_geometrico import calcular_errores, evaluar_preacople


def cargar_estaciones(archivo):
    estaciones = {}

    with open(archivo, newline="", encoding="utf-8-sig") as f:
        for fila in csv.DictReader(f):
            nombre = fila["estacion"].strip()

            if nombre in estaciones:
                raise ValueError(f"Estación duplicada: {nombre}")

            valores = {
                campo: float(fila[campo])
                for campo in (
                    "pre_x", "pre_y", "pre_yaw",
                    "final_x", "final_y", "final_yaw"
                )
            }

            if not all(math.isfinite(v) for v in valores.values()):
                raise ValueError(f"Valores no finitos en {nombre}")

            estaciones[nombre] = valores

    if not estaciones:
        raise ValueError("No hay estaciones configuradas")

    return estaciones


class Supervisor(Node):

    def __init__(self):
        super().__init__("supervisor_nav2_difuso")

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(
            self.tf_buffer, self
        )

        self.nav2 = ActionClient(
            self,
            NavigateToPose,
            "/navigate_to_pose"
        )

    def consultar_pose(self):
        transformacion = self.tf_buffer.lookup_transform(
            "map",
            "base_footprint",
            Time(),
            timeout=Duration(seconds=0.1)
        )

        p = transformacion.transform.translation
        q = transformacion.transform.rotation

        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        )

        return p.x, p.y, yaw


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--archivo",
        type=Path,
        default=(
            Path(__file__).resolve().parents[2]
            / "datos/objetivos_acoplamiento.csv"
        )
    )

    parser.add_argument(
        "--estacion",
        choices=["E1", "E2", "E3", "E4", "E5"],
        default="E1"
    )

    args = parser.parse_args()

    estaciones = cargar_estaciones(args.archivo)
    if args.estacion not in estaciones:
        parser.error(f"No existe {args.estacion} en el CSV")

    destino = estaciones[args.estacion]

    print(f"===== SUPERVISOR {args.estacion} =====", flush=True)
    print(
        f"Preacople: "
        f"({destino['pre_x']:.3f}, "
        f"{destino['pre_y']:.3f})",
        flush=True
    )
    print(
        f"Acople final: "
        f"({destino['final_x']:.3f}, "
        f"{destino['final_y']:.3f})",
        flush=True
    )

    rclpy.init()
    nodo = Supervisor()

    try:
        disponible = nodo.nav2.wait_for_server(
            timeout_sec=5.0
        )

        print(
            "Servidor Nav2:",
            "DISPONIBLE" if disponible else "NO DISPONIBLE",
            flush=True
        )

        # Esperar brevemente a que TF2 reciba las transformaciones.
        limite = time.monotonic() + 8.0
        pose = None

        while rclpy.ok() and time.monotonic() < limite:
            rclpy.spin_once(nodo, timeout_sec=0.1)

            try:
                pose = nodo.consultar_pose()
                break
            except TransformException:
                pass

        if pose is None:
            print("TF2: NO DISPONIBLE")
            return 1

        x, y, yaw = pose

        print(
            f"Pose actual: x={x:.3f}, "
            f"y={y:.3f}, "
            f"yaw={math.degrees(yaw):.2f} grados",
            flush=True
        )

        errores = calcular_errores(
            x, y, yaw,
            destino["final_x"],
            destino["final_y"],
            math.radians(destino["final_yaw"])
        )

        apto, motivo = evaluar_preacople(errores)

        print(
            f"Error longitudinal: "
            f"{errores['longitudinal']:.3f} m"
        )
        print(
            f"Error lateral: "
            f"{errores['lateral']:.3f} m"
        )
        print(
            f"Error angular: "
            f"{math.degrees(errores['angular']):.2f} grados"
        )

        print("Estado:", motivo)
        print("Movimiento enviado: NO")
        print("Control difuso activado: NO")

        return 0

    finally:
        nodo.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
