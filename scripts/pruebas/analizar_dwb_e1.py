import math
from collections import defaultdict

import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

RUTA = "datos/registros/diagnostico_dwb_e1"

reader = rosbag2_py.SequentialReader()
reader.open(
    rosbag2_py.StorageOptions(uri=RUTA, storage_id="sqlite3"),
    rosbag2_py.ConverterOptions(
        input_serialization_format="cdr",
        output_serialization_format="cdr"
    )
)

tipos = {
    t.name: get_message(t.type)
    for t in reader.get_all_topics_and_types()
}

velocidades = defaultdict(list)
evaluaciones = 0
con_trayectorias = 0
sin_trayectorias = 0
mejores_validas = 0
mejores_invalidas = 0
ejemplos = []

while reader.has_next():
    topic, data, timestamp = reader.read_next()

    if topic not in tipos:
        continue

    if topic in ("/cmd_vel_nav", "/cmd_vel"):
        msg = deserialize_message(data, tipos[topic])
        velocidades[topic].append(
            (msg.linear.x, msg.angular.z)
        )

    elif topic == "/evaluation":
        msg = deserialize_message(data, tipos[topic])
        evaluaciones += 1

        cantidad = len(msg.twists)

        if cantidad:
            con_trayectorias += 1
        else:
            sin_trayectorias += 1

        indice = msg.best_index

        if 0 <= indice < cantidad:
            mejor = msg.twists[indice]
            if mejor.total >= 0:
                mejores_validas += 1
            else:
                mejores_invalidas += 1

        if len(ejemplos) < 5:
            ejemplos.append(
                (cantidad, indice)
            )

print("===== VELOCIDADES =====")

for topic, datos in velocidades.items():
    total = len(datos)
    no_cero = sum(
        abs(v) > 0.001 or abs(w) > 0.001
        for v, w in datos
    )

    print(f"\n{topic}")
    print("Mensajes:", total)
    print("Comandos no nulos:", no_cero)

    if datos:
        print(
            "Máxima velocidad lineal:",
            max(abs(v) for v, w in datos)
        )
        print(
            "Máxima velocidad angular:",
            max(abs(w) for v, w in datos)
        )

print("\n===== EVALUACIONES DWB =====")
print("Evaluaciones:", evaluaciones)
print("Con trayectorias:", con_trayectorias)
print("Sin trayectorias:", sin_trayectorias)
print("Mejores válidas:", mejores_validas)
print("Mejores inválidas:", mejores_invalidas)
print("Ejemplos (trayectorias, mejor índice):", ejemplos)

print("\nRESULTADO: ANALISIS_COMPLETADO")
