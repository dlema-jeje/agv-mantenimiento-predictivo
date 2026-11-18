cmake_minimum_required(VERSION 3.8)
project(agv_avance3)

find_package(ament_cmake REQUIRED)

get_filename_component(repo "${CMAKE_CURRENT_SOURCE_DIR}/../../.." ABSOLUTE)
set(dest "share/${PROJECT_NAME}")
install(FILES "${repo}/launch/avance3.launch.py" DESTINATION "${dest}/launch")
install(FILES "${repo}/mundos/planta_bombeo_agv.world" DESTINATION "${dest}/mundos")
install(FILES
  "${repo}/datos/matriz_distancias.csv"
  "${repo}/datos/objetivos_acoplamiento.csv"
  DESTINATION "${dest}/datos")
install(FILES "${repo}/datos/final/ventanas_prueba.npz" DESTINATION "${dest}/datos/final")
install(FILES "${repo}/modelos/diagnostico.npz" DESTINATION "${dest}/modelos")
install(FILES "${repo}/scripts/priorizador_agv.py" DESTINATION "${dest}/scripts")
install(FILES "${repo}/scripts/sensores/emulador_rangos_frontales.py" DESTINATION "${dest}/scripts/sensores")
install(FILES "${repo}/scripts/difuso/controlador_agv_calibrado.py" DESTINATION "${dest}/scripts/difuso")
install(FILES "${repo}/scripts/integracion/secuencia_acoplamiento.py" DESTINATION "${dest}/scripts/integracion")
install(FILES
  "${repo}/scripts/final/caracteristicas.py"
  "${repo}/scripts/final/diagnostico.py"
  "${repo}/scripts/final/rondas.py"
  "${repo}/scripts/final/nodos.py"
  "${repo}/scripts/final/inspeccionar.py"
  "${repo}/scripts/final/spawn_waffle.py"
  DESTINATION "${dest}/scripts/final")
ament_package()
