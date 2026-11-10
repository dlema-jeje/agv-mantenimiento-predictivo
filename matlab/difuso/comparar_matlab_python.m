% Comparacion del controlador Mamdani
% Proyecto 4 - Avance 2

clear; clc;

fis = readfis('matlab/difuso/acople_agv.fis');

datos = readtable( ...
    'entrega_avance2/comparacion/diez_entradas_python.csv');

entradas = [
    datos.ed_m, ...
    datos.et_grados
];

salidas_matlab = evalfis(fis, entradas);

datos.v_matlab_m_s = salidas_matlab(:,1);
datos.w_matlab_rad_s = salidas_matlab(:,2);

datos.error_v = abs( ...
    datos.v_matlab_m_s - datos.v_python_m_s);

datos.error_w = abs( ...
    datos.w_matlab_rad_s - datos.w_python_rad_s);

% Umbrales: 2 % del rango de cada salida
limite_v = 0.004;
limite_w = 0.032;

datos.aprobado = ...
    datos.error_v < limite_v & ...
    datos.error_w < limite_w;

disp(datos);

writetable( ...
    datos, ...
    'entrega_avance2/comparacion/comparacion_matlab_python.csv');

fprintf('CASOS_APROBADOS: %d/10\n', ...
    sum(datos.aprobado));

fprintf('ERROR_MAX_V: %.8f\n', max(datos.error_v));
fprintf('ERROR_MAX_W: %.8f\n', max(datos.error_w));
