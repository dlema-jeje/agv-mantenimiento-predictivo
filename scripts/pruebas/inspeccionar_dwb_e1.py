import sqlite3
from rclpy.serialization import deserialize_message
from dwb_msgs.msg import LocalPlanEvaluation

ruta = (
    "datos/registros/diagnostico_dwb_e1/"
    "diagnostico_dwb_e1_0.db3"
)

conexion = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
cursor = conexion.cursor()

topic = cursor.execute(
    "SELECT id FROM topics WHERE name='/evaluation'"
).fetchone()

if topic is None:
    raise RuntimeError("No existe /evaluation")

topic_id = topic[0]

total = cursor.execute(
    "SELECT COUNT(*) FROM messages WHERE topic_id=?",
    (topic_id,)
).fetchone()[0]

print("Evaluaciones disponibles:", total, flush=True)

indices = sorted(set([0, total // 2, total - 1]))

for indice in indices:
    fila = cursor.execute(
        """
        SELECT data FROM messages
        WHERE topic_id=?
        ORDER BY timestamp
        LIMIT 1 OFFSET ?
        """,
        (topic_id, indice)
    ).fetchone()

    if fila is None:
        continue

    msg = deserialize_message(fila[0], LocalPlanEvaluation)

    print(f"\n===== EVALUACION {indice + 1}/{total} =====", flush=True)
    print("Trayectorias:", len(msg.twists))
    print("Mejor índice:", msg.best_index)
    print("Peor índice:", msg.worst_index)

    if 0 <= msg.best_index < len(msg.twists):
        mejor = msg.twists[msg.best_index]
        print("Puntuación total:", mejor.total)
        print("Velocidad seleccionada:", mejor.traj.velocity)

        for critic in mejor.scores:
            print(
                f"  {critic.name}: "
                f"raw={critic.raw_score:.4f}, "
                f"scale={critic.scale:.4f}"
            )

    del msg

conexion.close()
print("\nRESULTADO: INSPECCION_DWB_COMPLETADA")
