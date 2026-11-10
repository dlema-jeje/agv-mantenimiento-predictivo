import math
import time

import rclpy
from rclpy.duration import Duration
from rclpy.time import Time
from rclpy.qos import qos_profile_sensor_data
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from tf2_ros import Buffer, TransformListener


class Diagnostico(Node):
    def __init__(self):
        super().__init__('verificar_costmap_e1')
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.mapa = None

        self.create_subscription(
            OccupancyGrid,
            '/local_costmap/costmap',
            self.recibir_mapa,
            10
        )

    def recibir_mapa(self, msg):
        self.mapa = msg

    def consultar(self, x, y):
        info = self.mapa.info
        ox = info.origin.position.x
        oy = info.origin.position.y
        q = info.origin.orientation
        yaw = math.atan2(
            2 * (q.w * q.z + q.x * q.y),
            1 - 2 * (q.y * q.y + q.z * q.z)
        )
        dx, dy = x - ox, y - oy
        mx = math.cos(yaw) * dx + math.sin(yaw) * dy
        my = -math.sin(yaw) * dx + math.cos(yaw) * dy
        ix = math.floor(mx / info.resolution)
        iy = math.floor(my / info.resolution)

        if not (0 <= ix < info.width and 0 <= iy < info.height):
            return 'FUERA_DEL_COSTMAP'

        valor = self.mapa.data[iy * info.width + ix]

        if valor < 0:
            return f'DESCONOCIDO ({valor})'
        if valor == 0:
            return 'LIBRE (0)'
        if valor >= 100:
            return f'OCUPADO ({valor})'
        return f'COSTE_INTERMEDIO ({valor})'


rclpy.init()
node = Diagnostico()

limite = time.monotonic() + 10.0
transformacion = None

while rclpy.ok() and time.monotonic() < limite:
    rclpy.spin_once(node, timeout_sec=0.2)

    if node.mapa is None:
        continue

    try:
        transformacion = node.tf_buffer.lookup_transform(
            node.mapa.header.frame_id,
            'map',
            Time(),
            timeout=Duration(seconds=0.2)
        )
        break
    except Exception:
        pass

if node.mapa is None or transformacion is None:
    print('ERROR: No se recibió costmap o transformación map->odom')
else:
    t = transformacion.transform.translation
    q = transformacion.transform.rotation

    yaw = math.atan2(
        2 * (q.w * q.z + q.x * q.y),
        1 - 2 * (q.y * q.y + q.z * q.z)
    )

    print('===== COSTMAP E1 =====')
    print('Frame:', node.mapa.header.frame_id)

    objetivos = [
        ('CANDIDATO 0.20', 0.20, -1.40),
        ('CANDIDATO 0.30', 0.30, -1.40),
        ('CANDIDATO 0.40', 0.40, -1.40),
        ('CANDIDATO 0.50', 0.50, -1.40),
        ('PREACOPLE ACTUAL', 0.65, -1.40),
        ('CANDIDATO 0.75', 0.75, -1.40),
        ('CANDIDATO 0.85', 0.85, -1.40),
        ('FINAL E1', 1.05, -1.40),
    ]

    for nombre, x, y in objetivos:
        xo = t.x + math.cos(yaw) * x - math.sin(yaw) * y
        yo = t.y + math.sin(yaw) * x + math.cos(yaw) * y

        print(f'\n{nombre}')
        print(f'Map:  ({x:.3f}, {y:.3f})')
        print(f'Odom: ({xo:.3f}, {yo:.3f})')
        print('Celda:', node.consultar(xo, yo))

node.destroy_node()
rclpy.shutdown()
