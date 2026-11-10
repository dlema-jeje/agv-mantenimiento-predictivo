import math
import sqlite3
from collections import defaultdict

from rclpy.serialization import deserialize_message
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

RUTA = (
    "datos/registros/diagnostico_dwb_e1/"
    "diagnostico_dwb_e1_0.db3"
)

conexion = sqlite3.connect(
    f"file:{RUTA}?mode=ro",
    uri=True
)

cursor = conexion.cursor()

tipos = {
    "/cmd_vel_nav": Twist,
    "/cmd_vel": Twist,
    "/odom": Odometry
}

ids = {}

for identificador, nombre in cursor.execute(
    "SELECT id, name FROM topics"
):
    if nombre in tipos:
        ids[identificador] = nombre

if not ids:
    raise RuntimeError("No se encontraron los tópicos esperados")

resultados = defaultdict(list)

for identificador, nombre in ids.items():
    print(f"Analizando {nombre}...", flush=True)

    consulta = """
        SELECT data
        FROM messages
        WHERE topic_id = ?
        ORDER BY timestamp
    """

    for (datos,) in cursor.execute(consulta, (identificador,)):
        mensaje = deserialize_message(datos, tipos[nombre])

        if nombre == "/odom":
            v = mensaje.twist.twist.linear.x
            w = mensaje.twist.twist.angular.z
        else:
            v = mensaje.linear.x
            w = mensaje.angular.z

        resultados[nombre].append((v, w))

conexion.close()

print("\n===== RESULTADOS =====")

for nombre, valores in resultados.items():
    total = len(valores)

    no_nulos = sum(
        abs(v) > 0.001 or abs(w) > 0.001
        for v, w in valores
    )

    max_v = max((abs(v) for v, w in valores), default=0)
    max_w = max((abs(w) for v, w in valores), default=0)

    print(f"\n{nombre}")
    print(f"Mensajes: {total}")
    print(f"Comandos/muestras no nulos: {no_nulos}")
    print(f"Velocidad lineal máxima: {max_v:.4f} m/s")
    print(f"Velocidad angular máxima: {max_w:.4f} rad/s")

print("\nRESULTADO: ANALISIS_VELOCIDADES_COMPLETADO")
