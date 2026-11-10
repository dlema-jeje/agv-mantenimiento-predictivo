import sqlite3
from collections import Counter

from rclpy.serialization import deserialize_message
from dwb_msgs.msg import LocalPlanEvaluation

ruta = (
    "datos/registros/diagnostico_dwb_e1/"
    "diagnostico_dwb_e1_0.db3"
)

con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)

topic = con.execute(
    "SELECT id FROM topics WHERE name='/evaluation'"
).fetchone()

if topic is None:
    raise RuntimeError("No existe el tópico /evaluation")

topic_id = topic[0]

total = con.execute(
    "SELECT COUNT(*) FROM messages WHERE topic_id=?",
    (topic_id,)
).fetchone()[0]

fila = con.execute(
    """
    SELECT data FROM messages
    WHERE topic_id=?
    ORDER BY timestamp
    LIMIT 1 OFFSET ?
    """,
    (topic_id, total // 2)
).fetchone()

msg = deserialize_message(fila[0], LocalPlanEvaluation)

con.close()

rechazos = Counter()
validas_avance = []
invalidas_avance = 0
sin_avance = 0

for trayectoria in msg.twists:
    vx = trayectoria.traj.velocity.x

    if vx <= 0.001:
        sin_avance += 1
        continue

    if trayectoria.total < 0:
        invalidas_avance += 1
        for critic in trayectoria.scores:
            if critic.raw_score < 0:
                rechazos[critic.name] += 1
    else:
        validas_avance.append(trayectoria)

print("===== ANALISIS DWB =====")
print("Trayectorias totales:", len(msg.twists))
print("Sin avance:", sin_avance)
print("Con avance inválidas:", invalidas_avance)
print("Con avance válidas:", len(validas_avance))

print("\n===== CRITICOS QUE RECHAZAN AVANCE =====")
for nombre, cantidad in rechazos.most_common():
    print(f"{nombre}: {cantidad}")

print("\n===== MEJORES TRAYECTORIAS DE AVANCE =====")
for t in sorted(validas_avance, key=lambda x: x.total)[:5]:
    print(
        f"vx={t.traj.velocity.x:.4f}, "
        f"w={t.traj.velocity.theta:.4f}, "
        f"costo={t.total:.4f}"
    )

print("\nRESULTADO: RECHAZOS_ANALIZADOS")
