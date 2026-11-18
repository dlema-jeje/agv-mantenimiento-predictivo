import ast
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]


class TestCadenciaSupervisor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.codigo = (
            RAIZ / "scripts/integracion/supervisor_autorizacion.py"
        ).read_text(encoding="utf-8")
        cls.arbol = ast.parse(cls.codigo)

    def test_evaluacion_periodica(self):
        llamadas = [
            nodo for nodo in ast.walk(self.arbol)
            if isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Attribute)
            and nodo.func.attr == "create_timer"
            and len(nodo.args) >= 2
            and isinstance(nodo.func.value, ast.Name)
            and nodo.func.value.id == "self"
        ]

        self.assertEqual(len(llamadas), 1)

        periodo = ast.literal_eval(llamadas[0].args[0])
        self.assertGreater(periodo, 0)
        self.assertLessEqual(periodo, 0.2)

    def test_estados_requeridos(self):
        for topico in (
            "/agv/estado_nav2",
            "/agv/estado_arbitro",
            "/agv/estado_preacoplamiento",
            "/odom",
            "/scan",
        ):
            with self.subTest(topico=topico):
                self.assertIn(f'"{topico}"', self.codigo)

    def test_no_autoriza_movimiento(self):
        self.assertIn('"NO_AUTORIZADO | "', self.codigo)
        self.assertNotIn(
            'self.pub.publish(Twist(',
            self.codigo,
        )

    def test_estados_obsoletos(self):
        for motivo in (
            "NAV2_ESTADO_OBSOLETO",
            "ARBITRO_OBSOLETO",
            "PREACOPLAMIENTO_OBSOLETO",
        ):
            with self.subTest(motivo=motivo):
                self.assertIn(motivo, self.codigo)

    def test_arbitro_bloqueado(self):
        codigo = (
            RAIZ / "scripts/integracion/arbitro_velocidades.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'if msg.data.strip().upper() != "STOP":',
            codigo,
        )


if __name__ == "__main__":
    unittest.main()
