import ast
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
CLIENTE = (
    RAIZ / "scripts/integracion/cliente_nav2_supervisado.py"
)


class TestIntegracionClienteNav2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.codigo = CLIENTE.read_text(encoding="utf-8")
        cls.arbol = ast.parse(cls.codigo)

        cls.clase = next(
            nodo for nodo in cls.arbol.body
            if isinstance(nodo, ast.ClassDef)
            and nodo.name == "ClienteSupervisado"
        )

        cls.ejecutar = next(
            nodo for nodo in cls.clase.body
            if isinstance(nodo, ast.FunctionDef)
            and nodo.name == "ejecutar"
        )

        cls.llamadas = [
            nodo for nodo in ast.walk(cls.ejecutar)
            if isinstance(nodo, ast.Call)
        ]

    def argumentos_validador(self):
        llamadas = [
            nodo for nodo in self.llamadas
            if isinstance(nodo.func, ast.Name)
            and nodo.func.id == "validar_finalizacion_nav2"
        ]
        self.assertEqual(len(llamadas), 1)
        return {
            kw.arg: kw.value
            for kw in llamadas[0].keywords
        }

    def test_importa_validador(self):
        self.assertTrue(any(
            isinstance(nodo, ast.ImportFrom)
            and nodo.module == "validacion_final_nav2"
            and any(
                alias.name == "validar_finalizacion_nav2"
                for alias in nodo.names
            )
            for nodo in self.arbol.body
        ))

    def test_usa_validador_en_ejecutar(self):
        self.argumentos_validador()

    def test_exige_todas_las_evidencias(self):
        argumentos = self.argumentos_validador()
        self.assertEqual(
            set(argumentos),
            {
                "exito_nav2",
                "cancelacion_solicitada",
                "stop_confirmado",
                "velocidad_lineal",
                "velocidad_angular",
                "antiguedad_odom",
            },
        )

    def test_stop_depende_del_arbitro(self):
        argumentos = self.argumentos_validador()
        expresion = ast.unparse(argumentos["stop_confirmado"])
        self.assertIn("stop_confirmado is True", expresion)
        self.assertIn("self.modo == 'STOP'", expresion)
        self.assertIn("self.estado_fresco()", expresion)

    def test_cancelacion_se_considera(self):
        argumentos = self.argumentos_validador()
        expresion = ast.unparse(
            argumentos["cancelacion_solicitada"]
        )
        self.assertIn("motivo is not None", expresion)

    def test_odom_faltante_se_considera(self):
        argumentos = self.argumentos_validador()
        for nombre in (
            "velocidad_lineal",
            "velocidad_angular",
            "antiguedad_odom",
        ):
            expresion = ast.unparse(argumentos[nombre])
            self.assertIn("self.odom is not None", expresion)
            self.assertIn("else None", expresion)

    def test_no_publica_finalizado_directamente(self):
        for llamada in self.llamadas:
            if not (
                isinstance(llamada.func, ast.Attribute)
                and llamada.func.attr == "publicar_estado_nav2"
            ):
                continue

            if not llamada.args:
                continue

            argumento = llamada.args[0]
            self.assertFalse(
                isinstance(argumento, ast.Constant)
                and argumento.value == "FINALIZADO",
                "FINALIZADO no debe publicarse directamente",
            )

    def test_publicador_en_topico_correcto(self):
        self.assertIn(
            '"/agv/estado_nav2"',
            self.codigo,
        )

    def test_arbitro_conserva_bloqueo(self):
        codigo = (
            RAIZ / "scripts/integracion/arbitro_velocidades.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'if msg.data.strip().upper() != "STOP":',
            codigo,
        )


if __name__ == "__main__":
    unittest.main()
