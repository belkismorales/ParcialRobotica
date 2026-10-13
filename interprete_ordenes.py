import csv
import time

import rclpy
import requests
from rclpy.node import Node

from custom_interfaces.srv import InterpretarOrden

from clasificador_kw import COLORES, OBJETOS, clasificar as clasificar_palabras_clave


class InterpreteOrdenes(Node):
    def __init__(self):
        super().__init__('interprete_ordenes')
        # FIX: la URL tenía sintaxis markdown "[url](url)" -> inválida
        self.declare_parameter('laya_url', 'http://192.168.1.100:8000')
        self.declare_parameter('preset', '')
        self.declare_parameter('timeout_ms', 500)
        self.declare_parameter('log_csv', 'latencia_p1.csv')
        self.url = self.get_parameter('laya_url').value
        self.preset = self.get_parameter('preset').value
        self.timeout_s = self.get_parameter('timeout_ms').value / 1000.0
        self.log_csv = self.get_parameter('log_csv').value
        self.srv = self.create_service(
            InterpretarOrden, '/interpretar_orden', self.handle)
        self.get_logger().info(f'Listo. LAYA={self.url} timeout={self.timeout_s}s')

    # ---- ÚNICO punto que habla con LAYA ---------------------------------
    def consultar_laya(self, frase):
        """Debe devolver (dict_decision, server_ms).
        Salida TIPADA: choice (accion/objeto/color), score (prioridad 0-3),
        yes/no (permitido). Sin generar texto.
        TODO: adaptar endpoint y cuerpo al formato de laya-serve
        (docs/http-api del repo oficial) y al preset del docente."""
        questions = {
            'accion':    {'type': 'choice', 'options': ['recoger', 'trasladar', 'otra']},
            'objeto':    {'type': 'choice', 'options': OBJETOS + ['ninguno']},
            'color':     {'type': 'choice', 'options': COLORES + ['ninguno']},
            'prioridad': {'type': 'score', 'levels': 3},   # 0,1,2
            'permitido': {'type': 'yesno', 'statement': 'La orden es segura y permitida'},
        }
        r = requests.post(f'{self.url}/predict',
                          json={'state': {'text': frase}, 'questions': questions,
                                'preset': self.preset},
                          timeout=self.timeout_s)
        r.raise_for_status()
        d = r.json()
        # TODO: mapear 'd' a los campos de abajo según la respuesta real
        out = dict(accion=d['accion'], objeto=d['objeto'], color=d['color'],
                   prioridad=int(d['prioridad']), permitido=bool(d['permitido']))
        return out, float(d.get('server_ms', d.get('latency_ms', 0.0)))

    def handle(self, req, res):
        t0 = time.perf_counter()
        degradado, server_ms = False, 0.0
        try:
            dec, server_ms = self.consultar_laya(req.frase)
        except Exception as e:   # timeout, red, JSON, KeyError... nunca esperar
            self.get_logger().warn(f'LAYA falló ({type(e).__name__}); modo degradado')
            dec, degradado = clasificar_palabras_clave(req.frase), True
        rtt_ms = (time.perf_counter() - t0) * 1000.0
        res.accion, res.objeto, res.color = dec['accion'], dec['objeto'], dec['color']
        res.prioridad, res.permitido = dec['prioridad'], dec['permitido']
        res.degradado, res.rtt_ms, res.server_ms = degradado, rtt_ms, server_ms
        res.causa = '' if res.permitido else 'orden no permitida o no entendida'
        with open(self.log_csv, 'a', newline='') as f:
            csv.writer(f).writerow([time.time(), req.frase, res.accion, res.objeto,
                                    res.color, res.prioridad, res.permitido,
                                    degradado, f'{rtt_ms:.1f}', f'{server_ms:.1f}'])
        return res


def main(args=None):
    rclpy.init(args=args)
    n = InterpreteOrdenes()
    try:
        rclpy.spin(n)
    finally:
        n.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
