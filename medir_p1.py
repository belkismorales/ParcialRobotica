"""Uso: python3 medir_p1.py frases.csv resultado_p1.csv [etiqueta]
Con /interpretar_orden corriendo, envía las 50 frases del docente, y escribe un CSV con la
decisión de LAYA (la que devolvió el nodo) y la del clasificador por palabras clave.
Imprime mediana y p95 (total, servidor y red). Corre 1 vez en calma y 1 bajo carga
(etiqueta: calma | carga) y guarda cada salida con su nombre."""
import csv, statistics as st, sys, time
import rclpy
from rclpy.node import Node
from custom_interfaces.srv import InterpretarOrden
from clasificador_kw import clasificar


def p95(x):
    x = sorted(x); return x[min(len(x) - 1, int(round(0.95 * (len(x) - 1))))]


def correcto(d, f):
    """Exactitud operativa: permitido correcto y, si es permitida,
    acción, objeto, color y prioridad correctos."""
    esp_perm = f['permitido_esperado'] == 'True'
    if d['permitido'] != esp_perm:
        return False
    if not esp_perm:
        return True
    return (d['accion'], d['objeto'], d['color'], int(d['prioridad'])) == (
        f['accion_esperada'], f['objeto_esperado'], f['color_esperado'], int(f['prioridad_esperada']))


def main():
    rclpy.init(); n = Node('medir_p1')
    cli = n.create_client(InterpretarOrden, '/interpretar_orden'); cli.wait_for_service()
    filas = list(csv.DictReader(open(sys.argv[1], encoding='utf-8-sig')))
    rtt, srv, ok_l, ok_k, out = [], [], 0, 0, []
    for f in filas:
        req = InterpretarOrden.Request(); req.frase = f['frase']
        t = time.perf_counter(); fut = cli.call_async(req)
        rclpy.spin_until_future_complete(n, fut); r = fut.result()
        e2e = (time.perf_counter() - t) * 1000
        rtt.append(e2e); srv.append(r.server_ms)
        L = dict(accion=r.accion, objeto=r.objeto, color=r.color, prioridad=r.prioridad, permitido=r.permitido)
        K = clasificar(f['frase'])
        lo, ko = correcto(L, f), correcto(K, f); ok_l += lo; ok_k += ko
        out.append([f['id'], f['frase'], r.accion, r.objeto, r.color, r.prioridad, r.permitido, r.degradado, lo,
                    K['accion'], K['objeto'], K['color'], K['prioridad'], K['permitido'], ko,
                    f'{e2e:.1f}', f'{r.server_ms:.1f}', f'{e2e - r.server_ms:.1f}'])
    w = csv.writer(open(sys.argv[2], 'w', newline='', encoding='utf-8'))
    w.writerow(['id', 'frase', 'laya_accion', 'laya_objeto', 'laya_color', 'laya_prioridad', 'laya_permitido',
                'degradado', 'laya_ok', 'kw_accion', 'kw_objeto', 'kw_color', 'kw_prioridad', 'kw_permitido', 'kw_ok',
                'rtt_total_ms', 'server_ms', 'red_ms']); w.writerows(out)
    net = [a - b for a, b in zip(rtt, srv)]
    print(f'Total   mediana={st.median(rtt):.1f}  p95={p95(rtt):.1f} ms')
    print(f'Servidor mediana={st.median(srv):.1f}  p95={p95(srv):.1f} ms')
    print(f'Red      mediana={st.median(net):.1f}  p95={p95(net):.1f} ms')
    print(f'Exactitud  LAYA={ok_l}/{len(filas)}  palabras clave={ok_k}/{len(filas)}')


if __name__ == '__main__':
    main()
