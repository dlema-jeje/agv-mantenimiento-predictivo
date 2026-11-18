% MEC451 - Avance 2
% Ejecutar desde la raiz del proyecto en MATLAB.
% No requiere ROS 2 ni Gazebo.

ruta_fis = fullfile('matlab', 'difuso', 'acople_agv.fis');
ruta_python = fullfile('entrega_avance2', 'comparacion', ...
    'diez_entradas_python.csv');
ruta_salida = fullfile('entrega_avance2', 'comparacion', ...
    'comparacion_final_matlab_python.csv');

fis = readfis(ruta_fis);
datos = readtable(ruta_python, 'TextType', 'string');

entradas = [datos.ed_m, datos.et_grados];
salidas = evalfis(fis, entradas);

resultado = datos;
resultado.v_matlab_m_s = salidas(:, 1);
resultado.w_matlab_rad_s = salidas(:, 2);

resultado.error_v = abs( ...
    resultado.v_python_m_s - resultado.v_matlab_m_s);

resultado.error_w = abs( ...
    resultado.w_python_rad_s - resultado.w_matlab_rad_s);

resultado.cumple_v = resultado.error_v < 0.004;
resultado.cumple_w = resultado.error_w < 0.032;
resultado.cumple_ambos = ...
    resultado.cumple_v & resultado.cumple_w;

writetable(resultado, ruta_salida);

disp(resultado);
fprintf('Casos conformes: %d/%d\n', ...
    sum(resultado.cumple_ambos), height(resultado));
fprintf('Error maximo v: %.6f m/s\n', max(resultado.error_v));
fprintf('Error maximo w: %.6f rad/s\n', max(resultado.error_w));
fprintf('CSV: %s\n', ruta_salida);
