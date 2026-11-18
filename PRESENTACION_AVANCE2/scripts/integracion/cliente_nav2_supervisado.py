#!/usr/bin/env python3
"""Cliente Nav2 con vigilancia continua y parada supervisada."""

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String
from nav_msgs.msg import Odometry
from seguridad_mision import (
    odometria_detenida,
    registrar_incidencia,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidencia_resultado_nav2 import RegistroMisionNav2
from vinculo_objetivo_nav2 import verificar_objetivo
from identidad_mision import crear_evidencia
from registro_resultados_nav2 import registrar_resultado


from validacion_final_nav2 import validar_finalizacion_nav2



def normalizar_estacion_nav2(valor):
    """Convierte identificadores 1/E1 a E1; rechaza otros valores."""
    if isinstance(valor, dict):
        valor = valor.get("estacion")

    if isinstance(valor, bool):
        raise ValueError("ESTACION_INVALIDA")

    identificador = str(valor).strip().upper()

    if identificador in ("1", "2", "3", "4", "5"):
        identificador = "E" + identificador

    if identificador not in ("E1", "E2", "E3", "E4", "E5"):
        raise ValueError("ESTACION_INVALIDA")

    return identificador


class ClienteSupervisado(Node):

    def __init__(self):
        super().__init__("cliente_nav2_supervisado_agv")

        self.cliente = ActionClient(
            self, NavigateToPose, "/navigate_to_pose"
        )

        self.modo = None
        self.t_modo = 0.0
        self.odom = None
        self.t_odom = 0.0
        self.progreso = None
        self.t_progreso = time.monotonic()

        self.create_subscription(
            String, "/agv/estado_arbitro",
            self.recibir_modo, 10
        )

        self.create_subscription(
            Odometry, "/odom", self.recibir_odom, 10
        )

        self.pub_estado_nav2 = self.create_publisher(
            String, "/agv/estado_nav2", 10
        )

        self.pub_modo = self.create_publisher(
            String, "/agv/modo_control", 10
        )

        self.pub_evidencia_mision = self.create_publisher(
            String, "/agv/evidencia_mision_nav2", 10
        )
        self._registro_mision = None
        self.pub_mision_activa = self.create_publisher(
            String, "/agv/mision_nav2_activa", 10
        )


    def publicar_estado_nav2(self, estado):
        mensaje = String()
        mensaje.data = estado
        self.pub_estado_nav2.publish(mensaje)

        registro = getattr(self, "_registro_mision", None)
        if registro is None or registro.finalizada:
            return

        if estado == "FINALIZADO":
            self.publicar_evidencia_mision(
                registro.estacion, "FINALIZADO"
            )
        elif estado in (
            "OBJETIVO_RECHAZADO",
            "RESULTADO_RECIBIDO_NO_AUTORIZADO",
        ):
            self.publicar_evidencia_mision(
                registro.estacion, estado
            )

    def recibir_odom(self, msg):
        self.odom = msg
        self.t_odom = time.monotonic()

    def parada_verificada(self):
        return (
            self.estado_fresco()
            and self.modo == "STOP"
            and odometria_detenida(
                self.odom, self.t_odom
            )
        )

    def recibir_modo(self, msg):
        self.modo = msg.data.strip().upper()
        self.t_modo = time.monotonic()

    def feedback(self, msg):
        distancia = msg.feedback.distance_remaining
        if not math.isfinite(distancia):
            return

        if (
            self.progreso is None
            or self.progreso - distancia >= 0.05
        ):
            self.progreso = distancia
            self.t_progreso = time.monotonic()

    def exclusivo(self):
        return self.count_publishers("/cmd_vel") == 1

    def estado_fresco(self):
        return (
            self.modo is not None
            and time.monotonic() - self.t_modo < 2.0
        )

    def comprobar(self):
        limite = time.monotonic() + 8.0
        while time.monotonic() < limite:
            rclpy.spin_once(self, timeout_sec=0.2)
            if (
                self.estado_fresco()
                and self.exclusivo()
                and self.odom is not None
                and time.monotonic() - self.t_odom < 0.5
            ):
                break

        nav2 = self.cliente.wait_for_server(timeout_sec=2.0)
        arbitro = self.estado_fresco()
        exclusivo = self.exclusivo()

        print(f"NAV2_DISPONIBLE: {nav2}")
        print(f"ARBITRO_DISPONIBLE: {arbitro}")
        print(f"MODO_ARBITRO: {self.modo}")
        print(f"PUBLICADOR_EXCLUSIVO: {exclusivo}")
        print(
            f"PARADA_VERIFICADA: "
            f"{self.parada_verificada()}"
        )
        print("OBJETIVO_ENVIADO: NO")
        print("MOVIMIENTO_SOLICITADO: NO")

        return nav2 and arbitro and exclusivo

    def solicitar_stop(self):
        mensaje = String()
        mensaje.data = "STOP"

        for _ in range(10):
            self.pub_modo.publish(mensaje)
            rclpy.spin_once(self, timeout_sec=0.1)

            if self.modo == "STOP" and self.estado_fresco():
                return True

        return False

    def vigilar(self, futuro, inicio, tiempo_maximo, sin_progreso):
        while rclpy.ok() and not futuro.done():
            rclpy.spin_once(self, timeout_sec=0.1)
            ahora = time.monotonic()

            if not self.estado_fresco():
                return "ESTADO_ARBITRO_OBSOLETO"

            if self.modo != "NAV2":
                return "MODO_ARBITRO_INCORRECTO"

            if not self.exclusivo():
                return "PUBLICADORES_MULTIPLES"

            if ahora - inicio > tiempo_maximo:
                return "TIEMPO_MAXIMO"

            if ahora - self.t_progreso > sin_progreso:
                return "SIN_PROGRESO"

        return None


    def publicar_evidencia_mision(self, estacion, estado):
        """Publica evidencia solo si existe una misión activa."""
        if not hasattr(self, "_registro_mision"):
            return

        if self._registro_mision is None:
            return

        if self._registro_mision.estacion != estacion:
            return

        if estado == "NO_CONFIRMADO":
            evidencia = self._registro_mision.evidencia_inicial()
        else:
            evidencia = self._registro_mision.evidencia_resultado(estado)

        mensaje = String()
        mensaje.data = evidencia
        self.pub_evidencia_mision.publish(mensaje)

    def ejecutar(self, estacion, tiempo_maximo, sin_progreso):
        estacion_mision = normalizar_estacion_nav2(estacion)
        self._registro_mision = RegistroMisionNav2(estacion_mision)

        mensaje_mision = String()
        mensaje_mision.data = crear_evidencia(
            estacion=estacion_mision,
            mision_id=self._registro_mision.mision_id,
            estado="NO_CONFIRMADO",
        )
        self.pub_mision_activa.publish(mensaje_mision)

        self.publicar_evidencia_mision(
            estacion_mision, "NO_CONFIRMADO"
        )
        self.publicar_estado_nav2("NO_CONFIRMADO")
        if not self.comprobar():
            raise RuntimeError("Diagnóstico previo no aprobado")

        if self.modo != "NAV2":
            raise RuntimeError(
                "Árbitro en STOP. No se envía el objetivo. "
                "La habilitación NAV2 requiere supervisión previa."
            )

        objetivo = NavigateToPose.Goal()
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.get_clock().now().to_msg()

        pose.pose.position.x = float(estacion["pre_x"])
        pose.pose.position.y = float(estacion["pre_y"])

        yaw = float(estacion["pre_yaw"])
        pose.pose.orientation.z = math.sin(yaw / 2)
        pose.pose.orientation.w = math.cos(yaw / 2)
        objetivo.pose = pose

        # Verificar el objetivo efectivamente construido antes
        # de enviarlo a Nav2. No se permite continuar si difiere
        # del punto de aproximación de la estación seleccionada.
        estacion_id = normalizar_estacion_nav2(
            estacion["estacion"]
        )

        registro_mision = getattr(self, "_registro_mision", None)
        if registro_mision is None:
            self.publicar_estado_nav2("OBJETIVO_RECHAZADO")
            self.get_logger().error("MISION_NAV2_NO_REGISTRADA")
            return

        vinculo = verificar_objetivo(
            estacion=estacion_id,
            mision_id=registro_mision.mision_id,
            objetivo_x=float(pose.pose.position.x),
            objetivo_y=float(pose.pose.position.y),
            objetivo_yaw_rad=2.0 * math.atan2(
                pose.pose.orientation.z,
                pose.pose.orientation.w,
            ),
        )

        if not vinculo.valido:
            self.publicar_estado_nav2("OBJETIVO_RECHAZADO")
            self.get_logger().error(
                "OBJETIVO_NAV2_NO_COINCIDE: " + vinculo.motivo
            )
            return

        futuro_envio = self.cliente.send_goal_async(
            objetivo,
            feedback_callback=self.feedback
        )

        rclpy.spin_until_future_complete(
            self, futuro_envio, timeout_sec=5.0
        )

        if not futuro_envio.done():
            self.solicitar_stop()
            raise RuntimeError(
                "No se confirmó la aceptación del objetivo"
            )

        manejador = futuro_envio.result()

        if manejador is None or not manejador.accepted:
            self.solicitar_stop()
            print("RESULTADO: OBJETIVO_RECHAZADO")
            self.publicar_estado_nav2("OBJETIVO_RECHAZADO")
            return

        print("OBJETIVO_ACEPTADO: SI")

        inicio = time.monotonic()
        self.t_progreso = inicio
        self.progreso = None

        futuro_resultado = manejador.get_result_async()

        motivo = self.vigilar(
            futuro_resultado,
            inicio,
            tiempo_maximo,
            sin_progreso
        )

        if motivo is not None:
            print(f"CANCELACION_SOLICITADA: {motivo}")

            futuro_cancelar = manejador.cancel_goal_async()
            rclpy.spin_until_future_complete(
                self, futuro_cancelar, timeout_sec=5.0
            )

        # STOP incluso si la cancelación no fue confirmada.
        stop_confirmado = self.solicitar_stop()
        print(f"STOP_CONFIRMADO: {stop_confirmado}")

        if futuro_resultado.done():
            resultado = futuro_resultado.result()
            if resultado is not None:
                registro = registrar_resultado(
                    estacion=estacion["estacion"],
                    objetivo_x=float(estacion["pre_x"]),
                    objetivo_y=float(estacion["pre_y"]),
                    objetivo_yaw=yaw,
                    codigo_estado=resultado.status,
                )
                print(
                    f"RESULTADO_NAV2: {registro['resultado']}"
                )
                print(
                    "EXITO_CONFIRMADO: "
                    f"{registro['exito_confirmado']}"
                )
                self.publicar_estado_nav2(
                      validar_finalizacion_nav2(
                          exito_nav2=(
                              registro["exito_confirmado"] is True
                          ),
                          cancelacion_solicitada=(motivo is not None),
                          stop_confirmado=(
                              stop_confirmado is True
                              and self.modo == "STOP"
                              and self.estado_fresco()
                          ),
                          velocidad_lineal=(
                              self.odom.twist.twist.linear.x
                              if self.odom is not None else None
                          ),
                          velocidad_angular=(
                              self.odom.twist.twist.angular.z
                              if self.odom is not None else None
                          ),
                          antiguedad_odom=(
                              time.monotonic() - self.t_odom
                              if self.odom is not None else None
                          ),
                      ).estado
                  )
                return

        self.publicar_estado_nav2("NO_CONFIRMADO")
        print("RESULTADO_NAV2: NO_CONFIRMADO")
        print("EXITO_CONFIRMADO: False")


def cargar_estacion(ruta, nombre):
    with open(ruta, newline="", encoding="utf-8") as archivo:
        for fila in csv.DictReader(archivo):
            if fila["estacion"] == nombre:
                return fila

    raise ValueError(f"Estación desconocida: {nombre}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--estacion", default="E1")
    parser.add_argument(
        "--objetivos",
        default="datos/objetivos_acoplamiento.csv"
    )
    parser.add_argument("--ejecutar", action="store_true")
    parser.add_argument(
        "--tiempo-maximo", type=float, default=120.0
    )
    parser.add_argument(
        "--sin-progreso", type=float, default=45.0
    )
    args = parser.parse_args()

    estacion = cargar_estacion(
        args.objetivos, args.estacion
    )

    rclpy.init()
    nodo = ClienteSupervisado()

    try:
        if args.ejecutar:
            raise RuntimeError(
                "EJECUCION_BLOQUEADA: faltan pruebas de "
                "cancelacion, parada y supervision continua"
            )
        else:
            nodo.comprobar()
    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
