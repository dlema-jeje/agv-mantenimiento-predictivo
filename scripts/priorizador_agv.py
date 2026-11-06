#!/usr/bin/env python3
"""Punto 1.4: reglas de prioridad + desempate por vecino más cercano Dijkstra.
No envía velocidades ni objetivos de movimiento; genera el plan de visitas.
Uso: python3 priorizador_agv.py --proyecto ~/agv_predictivo --caso 1
"""
import argparse
import csv
import math
from pathlib import Path

ESTACIONES = [f'E{i}' for i in range(1, 6)]
CASOS = {
    1: [('Media',3,'Normal'), ('Alta',2,'Falla'), ('Baja',8,'Normal'), ('Alta',6,'Normal'), ('Baja',1,'Normal')],
    2: [('Alta',7,'Normal'), ('Alta',9,'Normal'), ('Alta',6,'Normal'), ('Baja',4,'Normal'), ('Baja',2,'Normal')],
    3: [('Media',8,'Normal'), ('Baja',10,'Normal'), ('Media',2,'Normal'), ('Alta',1,'Normal'), ('Baja',4,'Falla')],
}
ESPERADOS = {1:['E2','E4','E1','E3','E5'],2:['E3','E2','E1','E4','E5'],3:['E5','E4','E3','E1','E2']}

def prioridad(criticidad, dias, diagnostico):
    c, d = criticidad.strip().lower(), diagnostico.strip().lower()
    if c not in ('alta','media','baja') or d not in ('normal','falla') or dias < 0:
        raise ValueError(f'Estado inválido: {criticidad}, {dias}, {diagnostico}')
    if d == 'falla': return 1, 'R1: falla'
    if c == 'alta' and dias > 5: return 2, 'R2: preventivo alta criticidad'
    if c == 'baja' and d == 'normal': return 4, 'R3: normal baja criticidad'
    return 3, 'R4: por defecto'

def leer_matriz(ruta):
    with ruta.open(newline='', encoding='utf-8-sig') as f:
        filas = [r for r in csv.reader(f) if any(v.strip() for v in r)]
    # Acepta matriz 6x6 con encabezados (Base,E1,..), o primera columna de etiquetas,
    # o matriz numérica 6x6 sin encabezados. El orden es Base,E1,E2,E3,E4,E5.
    orden = ['Base'] + ESTACIONES
    if len(filas) == 7 and len(filas[0]) == 7:
        cab = [s.strip() for s in filas[0][1:]]
        if cab != orden: raise ValueError(f'Encabezado de matriz inesperado: {cab}')
        if [r[0].strip() for r in filas[1:]] != orden: raise ValueError('Etiquetas de filas incorrectas')
        datos = [r[1:] for r in filas[1:]]
    elif len(filas) == 7 and len(filas[0]) == 6:
        if [s.strip() for s in filas[0]] != orden: raise ValueError('Encabezado de matriz inesperado')
        datos = filas[1:]
    elif len(filas) == 6 and all(len(r) == 7 for r in filas):
        if [r[0].strip() for r in filas] != orden: raise ValueError('Etiquetas de filas incorrectas')
        datos = [r[1:] for r in filas]
    elif len(filas) == 6 and all(len(r) == 6 for r in filas):
        datos = filas
    else:
        raise ValueError('Formato no reconocido: se requiere matriz de 6x6 en orden Base,E1,...,E5')
    m = [[float(v) for v in r] for r in datos]
    if any(len(r)!=6 for r in m): raise ValueError('Dimensiones de matriz incorrectas')
    for i in range(6):
        if not math.isfinite(m[i][i]) or abs(m[i][i]) > 1e-4: raise ValueError('Diagonal inválida')
        for j in range(6):
            if not math.isfinite(m[i][j]) or m[i][j] < 0: raise ValueError('Distancia inválida')
            if abs(m[i][j]-m[j][i]) > 0.02: raise ValueError('Matriz no simétrica')
    return {a:{b:m[i][j] for j,b in enumerate(orden)} for i,a in enumerate(orden)}

def leer_estados(ruta):
    with ruta.open(newline='', encoding='utf-8-sig') as f:
        lector = csv.DictReader(f)
        requeridos = {'estacion','criticidad','dias','diagnostico'}
        if not lector.fieldnames or not requeridos.issubset(set(lector.fieldnames)):
            raise ValueError(f'CSV debe tener columnas {sorted(requeridos)}')
        datos = {}
        for r in lector:
            e = r['estacion'].strip().upper()
            if e in datos or e not in ESTACIONES: raise ValueError(f'Estación inválida/duplicada: {e}')
            datos[e] = (r['criticidad'], int(r['dias']), r['diagnostico'])
    if set(datos) != set(ESTACIONES): raise ValueError('Se requieren exactamente E1..E5')
    return datos

def ordenar(estados, matriz):
    pendientes = set(ESTACIONES)
    actual = 'Base'
    salida = []
    while pendientes:
        opciones = []
        for e in pendientes:
            p, regla = prioridad(*estados[e])
            opciones.append((p, matriz[actual][e], e, regla))
        p, distancia, e, regla = min(opciones, key=lambda x:(x[0], x[1], x[2]))
        salida.append({'orden':len(salida)+1,'desde':actual,'estacion':e,'prioridad':p,
                       'regla':regla,'distancia_m':distancia})
        pendientes.remove(e)
        actual = e
    return salida

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--proyecto',type=Path,default=Path.home()/'agv_predictivo')
    grupo=ap.add_mutually_exclusive_group(required=True)
    grupo.add_argument('--caso',type=int,choices=(1,2,3))
    grupo.add_argument('--estados',type=Path,help='CSV con estacion,criticidad,dias,diagnostico')
    args=ap.parse_args()
    matriz=leer_matriz(args.proyecto/'datos'/'matriz_distancias.csv')
    estados=dict(zip(ESTACIONES,CASOS[args.caso])) if args.caso else leer_estados(args.estados)
    plan=ordenar(estados,matriz)
    print('ORDEN:', ' -> '.join(['Base']+[r['estacion'] for r in plan]))
    for r in plan:
        print(f"{r['orden']}. {r['desde']} -> {r['estacion']} | P={r['prioridad']} | "
              f"{r['distancia_m']:.3f} m | {r['regla']}")
    print(f"Distancia total sin regreso: {sum(r['distancia_m'] for r in plan):.3f} m")
    if args.caso:
        obtenido=[r['estacion'] for r in plan]
        print('VALIDACIÓN DEL CASO:', 'COINCIDE CON INFORME' if obtenido==ESPERADOS[args.caso] else 'DIFIERE DEL INFORME')
    salida=args.proyecto/'datos'/'orden_priorizado.csv'
    with salida.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['orden','desde','estacion','prioridad','regla','distancia_m'])
        writer.writeheader(); writer.writerows(plan)
    print('Guardado:', salida)

if __name__=='__main__': main()
