"""Clasificador por palabras clave (respaldo). Python puro: se prueba sin ROS."""
import re
import unicodedata

COLORES = ['rojo', 'azul', 'verde', 'amarillo']      # los 4 de la mesa
OBJETOS = ['cubo', 'cilindro']                        # los de la mesa
RECOGER = ['recoge', 'recoger', 'agarra', 'agarrar', 'toma', 'coge', 'levanta']
TRASLADAR = ['lleva', 'llevar', 'mueve', 'muevas', 'mover', 'coloca', 'pasa',
             'deposita', 'traslada', 'trasladar', 'saca', 'pon', 'ponlo', 'dejalo']
PROHIBIDAS = ['destruye', 'lanza', 'empuja', 'golpea', 'quema', 'tira', 'aplasta',
              'rompe', 'suelta', 'sacude']
URGENTES = ['urgente', 'ya', 'rapido', 'inmediatamente', 'inmediato', 'emergencia',
            'alta']


def norm(s):
    s = unicodedata.normalize('NFD', s.lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def clasificar(frase):
    palabras = re.findall(r'[a-z]+', norm(frase))      # palabras completas (evita 'ya' en 'playa')
    ps = set(palabras)
    accion = 'desconocida'
    if ps & set(RECOGER):
        accion = 'recoger'
    elif ps & set(TRASLADAR):
        accion = 'trasladar'
    verbo_malo = next((p for p in palabras if any(p.startswith(k[:-1]) for k in PROHIBIDAS)), None)
    if verbo_malo:
        accion = verbo_malo
    objeto = next((o for o in OBJETOS if o in ps), 'desconocido')
    color = next((c for c in COLORES if c in ps), 'desconocido')
    ok_tipo = accion in ('recoger', 'trasladar')
    permitido = ok_tipo and objeto != 'desconocido' and color != 'desconocido'
    prioridad = 0 if not permitido else (2 if ps & set(URGENTES) or 'de inmediato' in ' '.join(palabras) else 1)
    return dict(accion=accion, objeto=objeto, color=color,
                prioridad=prioridad, permitido=permitido)
