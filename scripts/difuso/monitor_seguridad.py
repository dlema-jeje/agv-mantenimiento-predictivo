#!/usr/bin/env python3
"""Monitor conservador para aproximación frontal del AGV."""

import math
import time

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.duration import Duration
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformListener, TransformException


def distancia_frontal(scan, semiangulo=math.radians(30)):
    """Distancia mínima válida dentro del sector frontal."""
    valores = []
    for i, distancia in enumerate(scan.ranges):
        angulo = scan.angle_min + i * scan.angle_increment
        angulo = math.atan2(math.sin(angulo), math.cos(angulo))
        if abs(angulo) <= semiangulo:
            if math.isfinite(distancia) and scan.range_min <= distancia <= scan.range_max:
                valores.append(distancia)
    return min(valores) if valores else None


class MonitorSeguridad(Node):
    def __init__(self):
        super().__init__("monitor_seguridad_acoplamiento")
        self.set_parameters([rclpy.parameter.Parameter("use_sim_time", value=True)])
        self.ultimo_scan = None
        self.instante_scan = None
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.create_subscription(LaserScan, "/scan", self.recibir_scan, 10)

    def recibir_scan(self, msg):
        self.ultimo_scan = msg
        self.instante_scan = time.monotonic()

    def evaluar(self):
        if self.ultimo_scan is None or self.instante_scan is None:
            return False, "SIN_LIDAR"

        if time.monotonic() - self.instante_scan > 1.0:
            return False, "LIDAR_DESACTUALIZADO"

        distancia = distancia_frontal(self.ultimo_scan)
        if distancia is None:
            return False, "SIN_LECTURAS_FRONTALES_VALIDAS"

        # Umbral provisional y conservador.
        # Debe ajustarse con la geometría real del robot y de la placa.
        if distancia < 0.30:
            return False, f"OBSTACULO_FRONTAL_{distancia:.3f}m"

        try:
            tf = self.tf_buffer.lookup_transform(
                "map", "base_footprint", Time(),
                timeout=Duration(seconds=0.1)
            )
        except TransformException:
            return False, "TF_NO_DISPONIBLE"

        # Evitar usar una transformación antigua.
        ahora_ros = self.get_clock().now().nanoseconds
        stamp = (
            tf.header.stamp.sec * 1_000_000_000
            + tf.header.stamp.nanosec
        )
        edad_ns = ahora_ros - stamp

        if stamp <= 0:
            return False, "TF_SIN_FECHA"

        if edad_ns < -200_000_000:
            return False, "TF_FECHA_FUTURA"

        if edad_ns > 1_000_000_000:
            return False, "TF_DESACTUALIZADA"

        return True, f"APTO_DISTANCIA_FRONTAL_{distancia:.3f}m"


def main():
    rclpy.init()
    nodo = MonitorSeguridad()
    try:
        limite = time.monotonic() + 8.0
        while rclpy.ok() and time.monotonic() < limite:
            rclpy.spin_once(nodo, timeout_sec=0.1)
            apto, motivo = nodo.evaluar()
            if apto or motivo not in (
                "SIN_LIDAR",
                "LIDAR_DESACTUALIZADO",
                "TF_NO_DISPONIBLE",
                "TF_DESACTUALIZADA",
            ):
                print(f"Seguridad: {'APTO' if apto else 'BLOQUEADO'}")
                print(f"Motivo: {motivo}")
                break
        else:
            print("Seguridad: BLOQUEADO")
            print("Motivo: DATOS_NO_DISPONIBLES")
    finally:
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
