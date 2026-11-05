from pathlib import Path
from xml.sax.saxutils import escape
out=Path(__file__).resolve().parents[1]/'mundos'/'planta_bombeo_agv.world'
parts=['''<?xml version="1.0"?>
<sdf version="1.6"><world name="planta_bombeo_agv">
<include><uri>model://sun</uri></include>
<include><uri>model://ground_plane</uri></include>
<physics type="ode"><real_time_update_rate>1000</real_time_update_rate><max_step_size>0.001</max_step_size></physics>
''']
def box(name,x,y,z,sx,sy,sz,color):
 return f'''<model name="{name}"><static>true</static><pose>{x} {y} {z} 0 0 0</pose><link name="link"><collision name="collision"><geometry><box><size>{sx} {sy} {sz}</size></box></geometry></collision><visual name="visual"><geometry><box><size>{sx} {sy} {sz}</size></box></geometry><material><ambient>{color} 1</ambient><diffuse>{color} 1</diffuse></material></visual></link></model>'''
def cyl(name,x,y,z,r,h):
 return f'''<model name="{name}"><static>true</static><pose>{x} {y} {z} 0 0 0</pose><link name="link"><collision name="collision"><geometry><cylinder><radius>{r}</radius><length>{h}</length></cylinder></geometry></collision><visual name="visual"><geometry><cylinder><radius>{r}</radius><length>{h}</length></cylinder></geometry><material><ambient>0.25 0.4 0.7 1</ambient></material></visual></link></model>'''
# Superficie nominal 5 x 4 m, sin paredes, para permitir inspección sin obstáculos artificiales.
parts.append(box('area_industrial',0,0,0.005,5,4,0.01,'0.6 0.62 0.64'))
for i,y in enumerate([-1.4,-0.7,0.0,0.7,1.4],1):
 parts.append(cyl(f'maquina_{i}',1.78,y,0.35,0.20,0.70))
 # placa frontal orientada perpendicular a X, 50 cm de ancho en Y y 20 cm de alto
 # centro Z=0.20, intervalo 0.10..0.30 m: validar con altura real de base_scan
 parts.append(box(f'placa_{i}',1.35,y,0.20,0.025,0.50,0.20,'0.9 0.5 0.12'))
parts.append('</world></sdf>')
out.write_text('\n'.join(parts),encoding='utf-8')
print(out)
