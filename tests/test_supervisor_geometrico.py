import sys
import math
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "scripts" / "difuso")
)

from supervisor_geometrico import (
    calcular_errores,
    evaluar_preacople,
    evaluar_acople,
)


class TestSupervisorGeometrico(unittest.TestCase):

    def test_preacople_valido(self):
        errores = calcular_errores(
            0.75, -1.4, 0.0,
            1.05, -1.4, 0.0
        )
        apto, motivo = evaluar_preacople(errores)
        self.assertTrue(apto, motivo)

    def test_lateral_excesivo(self):
        errores = calcular_errores(
            0.75, -1.35, 0.0,
            1.05, -1.4, 0.0
        )
        apto, motivo = evaluar_preacople(errores)
        self.assertFalse(apto)
        self.assertEqual(motivo, "ERROR_LATERAL_EXCESIVO")

    def test_angular_excesivo(self):
        errores = calcular_errores(
            0.75, -1.4, math.radians(15),
            1.05, -1.4, 0.0
        )
        apto, motivo = evaluar_preacople(errores)
        self.assertFalse(apto)
        self.assertEqual(motivo, "ERROR_ANGULAR_EXCESIVO")

    def test_objetivo_sobrepasado(self):
        errores = calcular_errores(
            1.06, -1.4, 0.0,
            1.05, -1.4, 0.0
        )
        apto, motivo = evaluar_preacople(errores)
        self.assertFalse(apto)
        self.assertEqual(motivo, "OBJETIVO_SOBREPASADO")

    def test_acople_exitoso(self):
        errores = calcular_errores(
            1.045, -1.4, math.radians(2),
            1.05, -1.4, 0.0
        )
        self.assertTrue(evaluar_acople(errores))


if __name__ == "__main__":
    unittest.main()
