"""Nodos de replay CWRU y diagnóstico. El identificador correlaciona cada visita."""
import argparse
import json

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from diagnostico import Diagnostico
from rondas import BancoPrueba, ROOT


def publicar(pub, datos):
    pub.publish(String(data=json.dumps(datos, allow_nan=False)))


class Acelerometro(Node):
    def __init__(self):
        super().__init__("acelerometro_sim")
        self.banco = BancoPrueba(ROOT / "datos/final/ventanas_prueba.npz")
        self.pub = self.create_publisher(String, "/acelerometro_sim/ventana", 10)
        self.create_subscription(String, "/inspeccion/acople_confirmado", self.recibir, 10)

    def recibir(self, msg):
        try:
            evento = json.loads(msg.data)
            indice, muestra = self.banco.leer(evento["ronda"], evento["estacion"])
            publicar(self.pub, {**evento, "fs": 12000, "ventana": indice,
                                "muestras": muestra.tolist()})
        except (TypeError, ValueError, KeyError) as exc:
            self.get_logger().error(f"Evento rechazado. {exc}")


class Diagnosticador(Node):
    def __init__(self):
        super().__init__("diagnosticador")
        self.modelo = Diagnostico(ROOT / "modelos/diagnostico.npz")
        self.pub = self.create_publisher(String, "/diagnostico", 10)
        self.create_subscription(String, "/acelerometro_sim/ventana", self.recibir, 10)

    def recibir(self, msg):
        try:
            datos = json.loads(msg.data)
            if datos["fs"] != 12000:
                raise ValueError("Frecuencia incompatible")
            clase, confianza = self.modelo.clasificar(datos["muestras"])
            publicar(self.pub, {k: datos[k] for k in ("id", "ronda", "estacion", "ventana")} |
                     {"clase": clase, "confianza": confianza})
        except (TypeError, ValueError, KeyError) as exc:
            self.get_logger().error(f"Ventana rechazada. {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("nodo", choices=("acelerometro", "diagnosticador"))
    args, ros_args = parser.parse_known_args()
    rclpy.init(args=ros_args)
    nodo = Acelerometro() if args.nodo == "acelerometro" else Diagnosticador()
    try:
        rclpy.spin(nodo)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
