#!/usr/bin/env python3

import math
from collections import deque

import rclpy
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node


OBJETIVO = (0.9015, -1.4)
INICIO = (-1.0158, 1.4564)


class DiagnosticoCostmap(Node):
    def __init__(self):
        super().__init__("diagnostico_costmap")

        self.subscription = self.create_subscription(
            OccupancyGrid,
            "/global_costmap/costmap",
            self.analizar,
            10,
        )
        self.terminado = False

    def analizar(self, msg):
        if self.terminado:
            return

        self.terminado = True

        info = msg.info
        width = info.width
        height = info.height
        data = msg.data

        def celda(x, y):
            col = math.floor(
                (x - info.origin.position.x) / info.resolution
            )
            fila = math.floor(
                (y - info.origin.position.y) / info.resolution
            )
            return col, fila

        def dentro(c):
            x, y = c
            return 0 <= x < width and 0 <= y < height

        def valor(c):
            x, y = c
            return data[y * width + x]

        inicio = celda(*INICIO)
        objetivo = celda(*OBJETIVO)

        print("\n===== DIAGNOSTICO COSTMAP GLOBAL =====")
        print(f"Frame: {msg.header.frame_id}")
        print(f"Dimensiones: {width} x {height}")
        print(f"Resolucion: {info.resolution}")
        print(f"Inicio: {inicio}")
        print(f"Objetivo E1: {objetivo}")

        if not dentro(inicio) or not dentro(objetivo):
            print("ERROR: inicio u objetivo fuera del mapa")
            return

        print(f"Coste inicio: {valor(inicio)}")
        print(f"Coste E1: {valor(objetivo)}")

        # Nav2 utiliza normalmente 254 para obstáculos letales,
        # 253 para zonas inscribibles y 255 para desconocidas.
        # Para esta prueba consideramos transitables las celdas
        # con coste entre 0 y 252.
        def libre(c):
            return dentro(c) and 0 <= valor(c) <= 252

        print(f"Inicio transitable: {libre(inicio)}")
        print(f"E1 transitable: {libre(objetivo)}")

        if not libre(inicio) or not libre(objetivo):
            print("RESULTADO: inicio u objetivo no transitable")
            return

        cola = deque([inicio])
        visitados = {inicio}

        movimientos = [
            (1, 0), (-1, 0),
            (0, 1), (0, -1),
        ]

        encontrado = False

        while cola:
            actual = cola.popleft()

            if actual == objetivo:
                encontrado = True
                break

            for dx, dy in movimientos:
                siguiente = (
                    actual[0] + dx,
                    actual[1] + dy,
                )

                if siguiente not in visitados and libre(siguiente):
                    visitados.add(siguiente)
                    cola.append(siguiente)

        print(f"Celdas exploradas: {len(visitados)}")

        if encontrado:
            print("RESULTADO: EXISTE CONEXION DE CELDAS TRANSITABLES")
        else:
            print("RESULTADO: NO EXISTE CONEXION DE CELDAS TRANSITABLES")


def main():
    rclpy.init()
    nodo = DiagnosticoCostmap()

    try:
        while rclpy.ok() and not nodo.terminado:
            rclpy.spin_once(nodo, timeout_sec=1.0)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
