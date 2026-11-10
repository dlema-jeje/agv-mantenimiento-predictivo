import sys
import math
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "scripts" / "difuso")
)

from controlador_agv import crear_simulacion


class TestControladorMamdani(unittest.TestCase):

    def test_salidas_en_rango(self):
        casos = [
            (0.40, 0.0),
            (0.30, 10.0),
            (0.30, -10.0),
            (0.15, 5.0),
            (0.15, -5.0),
            (0.05, 0.0),
            (0.00, 0.0),
        ]

        for ed, et in casos:
            with self.subTest(ed=ed, et=et):
                simulacion = crear_simulacion()
                simulacion.input["ed"] = ed
                simulacion.input["et"] = et
                simulacion.compute()

                v = float(simulacion.output["v"])
                w = float(simulacion.output["w"])

                self.assertTrue(math.isfinite(v))
                self.assertTrue(math.isfinite(w))

                self.assertGreaterEqual(v, -0.05 - 1e-6)
                self.assertLessEqual(v, 0.15 + 1e-6)
                self.assertGreaterEqual(w, -0.8 - 1e-6)
                self.assertLessEqual(w, 0.8 + 1e-6)

    def test_simetria_aproximada_giro(self):
        izquierda = crear_simulacion()
        derecha = crear_simulacion()

        izquierda.input["ed"] = 0.25
        izquierda.input["et"] = 10.0
        izquierda.compute()

        derecha.input["ed"] = 0.25
        derecha.input["et"] = -10.0
        derecha.compute()

        wi = float(izquierda.output["w"])
        wd = float(derecha.output["w"])

        self.assertAlmostEqual(wi, -wd, delta=0.15)


if __name__ == "__main__":
    unittest.main()
