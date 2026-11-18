#!/usr/bin/env python3
"""Evaluador ROS 2 de preacoplamiento. Solo diagnóstico; sin movimiento."""

import argparse
import csv
import json
from identidad_mision import verificar_evidencia
import math
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformListener

from evaluador_preacoplamiento import evaluar_pose_preacoplamiento_con_vigencia


RAIZ = Path(__file__).resolve().parents[2]
OBJETIVOS = RAIZ / "datos" / "objetivos_acoplamiento.csv"


def cargar_objetivo(estacion):
    with OBJETIVOS.open(newline="", encoding="utf-8") as archivo:
        for fila in csv.DictReader(archivo):
            if fila["estacion"] == estacion:
                return {
                    "pre_x": float(fila["pre_x"]),
                    "pre_y": float(fila["pre_y"]),
                    "pre_yaw": math.radians(float(fila["pre_yaw"])),
                    "final_x": float(fila["final_x"]),
                    "final_y": float(fila["final_y"]),
                    "final_yaw": math.radians(float(fila["final_yaw"])),
                }
    raise ValueError(f"Estación no encontrada: {estacion}")


def yaw_cuaternion(q):
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z),
    )


class NodoPreacoplamiento(Node):
    def __init__(self, estacion):
        super().__init__("evaluador_preacoplamiento")

        self.estacion = estacion
        self.mision_activa = None
        self.evidencia_nav2 = None
        self.objetivo = cargar_objetivo(estacion)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.estado_nav2 = None
        self.estado_arbitro = None
        self.t_nav2 = 0.0
        self.t_arbitro = 0.0
        self.t_odom = 0.0
        self.t_sensores = 0.0

        self.odom = None
        self.scan = None

        self.pub_estado = self.create_publisher(
            String, "/agv/estado_preacoplamiento", 10
        )
        self.pub_errores = self.create_publisher(
            String, "/agv/errores_acoplamiento", 10
        )

        self.create_subscription(
            String, "/agv/estado_nav2", self.recibir_nav2, 10
        )
        self.create_subscription(
            String, "/agv/estado_arbitro", self.recibir_arbitro, 10
        )
        self.create_subscription(
            Odometry, "/odom", self.recibir_odom, 10
        )
        self.create_subscription(
            LaserScan, "/scan", self.recibir_scan, 10
        )

        self.create_timer(0.2, self.evaluar)

        self.create_subscription(
            String,
            "/agv/mision_nav2_activa",
            self.recibir_mision_activa,
            10,
        )
        self.create_subscription(
            String,
            "/agv/evidencia_mision_nav2",
            self.recibir_evidencia_nav2,
            10,
        )


    def recibir_nav2(self, msg):
        self.estado_nav2 = msg.data.strip()
        self.t_nav2 = time.monotonic()

    def recibir_arbitro(self, msg):
        self.estado_arbitro = msg.data.strip()
        self.t_arbitro = time.monotonic()

    def recibir_odom(self, msg):
        self.odom = msg
        self.t_odom = time.monotonic()

    def recibir_scan(self, msg):
        self.scan = msg
        self.t_sensores = time.monotonic()

    def sensores_validos(self):
        if self.scan is None:
            return False
        return any(
            math.isfinite(r)
            and self.scan.range_min <= r <= self.scan.range_max
            for r in self.scan.ranges
        )

    def robot_detenido(self):
        if self.odom is None:
            return False
        twist = self.odom.twist.twist
        return (
            abs(twist.linear.x) < 0.01
            and abs(twist.angular.z) < 0.03
        )

    def recibir_mision_activa(self, msg):
        self.mision_activa = None
        self.evidencia_nav2 = None

        try:
            datos = json.loads(msg.data)
            if not isinstance(datos, dict):
                return

            if datos.get("estacion") != self.estacion:
                return

            if datos.get("estado") != "NO_CONFIRMADO":
                return

            identificador = datos.get("mision_id")
            if not isinstance(identificador, str):
                return

            # Validar el formato mediante la función existente.
            from identidad_mision import crear_evidencia
            crear_evidencia(
                estacion=self.estacion,
                mision_id=identificador,
                estado="NO_CONFIRMADO",
            )
            self.mision_activa = datos

        except (ValueError, TypeError):
            return

    def recibir_evidencia_nav2(self, msg):
        self.evidencia_nav2 = None

        if self.mision_activa is None:
            return

        resultado = verificar_evidencia(
            mensaje=msg.data,
            estacion_esperada=self.estacion,
            mision_esperada=self.mision_activa["mision_id"],
        )

        if resultado.valida:
            self.evidencia_nav2 = resultado

    def nav2_mision_confirmada(self):
        return (
            self.mision_activa is not None
            and self.evidencia_nav2 is not None
            and self.evidencia_nav2.valida
            and self.evidencia_nav2.mision_id
                == self.mision_activa["mision_id"]
        )

    def evaluar(self):
        ahora = time.monotonic()
        estado = "NO_CONFIRMADO"
        nav2_identificado = self.nav2_mision_confirmada()
        evidencia = {
            "valido": False,
            "motivo": "SIN_EVIDENCIA_GEOMETRICA",
            "error_distancia_m": None,
            "error_angular_rad": None,
            "error_lateral_m": None,
            "estacion": self.estacion,
        }

        try:
            tf = self.tf_buffer.lookup_transform(
                "map", "base_footprint", rclpy.time.Time()
            )

            p = tf.transform.translation
            yaw = yaw_cuaternion(tf.transform.rotation)

            resultado, errores, _, vigencia = (
                evaluar_pose_preacoplamiento_con_vigencia(
                    x=p.x,
                    y=p.y,
                    yaw=yaw,
                    objetivo_x=self.objetivo["final_x"],
                    objetivo_y=self.objetivo["final_y"],
                    objetivo_yaw=self.objetivo["final_yaw"],
                    ahora=time.monotonic(),
                    t_nav2=(ahora if nav2_identificado else 0.0),
                    t_arbitro=self.t_arbitro,
                    t_odom=self.t_odom,
                    t_sensores=self.t_sensores,
                    estado_nav2=(
                            "FINALIZADO"
                            if nav2_identificado
                            else "NO_CONFIRMADO"
                        ),
                    estado_arbitro=self.estado_arbitro,
                    sensores_validos=self.sensores_validos(),
                    robot_detenido=self.robot_detenido(),
                )
            )

            distancia_aproximacion = math.hypot(
                p.x - self.objetivo["pre_x"],
                p.y - self.objetivo["pre_y"],
            )

            error_yaw_aproximacion = math.atan2(
                math.sin(yaw - self.objetivo["pre_yaw"]),
                math.cos(yaw - self.objetivo["pre_yaw"]),
            )

            aproximacion_correcta = (
                distancia_aproximacion <= 0.10
                and abs(error_yaw_aproximacion) <= math.radians(10)
            )

            if (
                resultado.confirmado
                and vigencia.valida
                and aproximacion_correcta
            ):
                if nav2_identificado:
                    estado = "POSE_APTA"

            # Los errores son respecto al objetivo final.
            # La evidencia solo es válida si se cumplen las
            # condiciones de vigencia, seguridad y estación.
            if errores is not None:
                evidencia = {
                    "valido": bool(
                        vigencia.valida
                        and aproximacion_correcta
                        and nav2_identificado
                    ),
                    "motivo": (
                        "EVIDENCIA_GEOMETRICA_VIGENTE"
                        if vigencia.valida and aproximacion_correcta
                        else "EVIDENCIA_NO_AUTORIZADA"
                    ),
                    "error_distancia_m": errores["longitudinal"],
                    "error_angular_rad": errores["angular"],
                    "error_lateral_m": errores["lateral"],
                    "estacion": self.estacion,
                }

        except Exception as exc:
            self.get_logger().debug(f"Preacoplamiento no confirmado: {exc}")

        mensaje = String()
        mensaje.data = estado
        self.pub_estado.publish(mensaje)

        mensaje_errores = String()
        mensaje_errores.data = json.dumps(
            evidencia,
            allow_nan=False,
        )
        self.pub_errores.publish(mensaje_errores)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--estacion",
        choices=["E1", "E2", "E3", "E4", "E5"],
        default="E1",
    )
    args = parser.parse_args()

    rclpy.init()
    nodo = NodoPreacoplamiento(args.estacion)

    try:
        rclpy.spin(nodo)
    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
