clc;
disp('==========================================');
disp('FASE 1 - PRUEBA REAL EN MATLAB R2026b');
disp('==========================================');

proyecto = fileparts(fileparts(fileparts(mfilename('fullpath'))));
archivo_fis = fullfile(proyecto, 'matlab', 'difuso', 'acople_agv.fis');

fprintf('Archivo FIS: %s\n', archivo_fis);

fis = readfis(archivo_fis);

fprintf('\nTipo de controlador: %s\n', class(fis));
fprintf('Entradas: %d\n', numel(fis.Inputs));
fprintf('Salidas: %d\n', numel(fis.Outputs));
fprintf('Reglas: %d\n', numel(fis.Rules));

disp(' ');
disp('PRUEBAS DE ENTRADA Y SALIDA:');
disp('ed [m]     et [grados]       v [m/s]       omega [rad/s]');

casos = [
    -0.04,   0;
     0.00,   0;
     0.04,  12;
     0.04, -12;
     0.15,   0;
     0.40,   0;
     0.40,  15;
     0.40, -15;
     0.20,   7;
     0.20,  -7
];

salidas = evalfis(fis, casos);

for k = 1:size(casos, 1)
    fprintf('%+8.3f    %+8.1f       %+10.6f      %+10.6f\n', ...
        casos(k,1), casos(k,2), salidas(k,1), salidas(k,2));
end

disp(' ');
disp('RESULTADO: MATLAB EVALUO LOS 10 CASOS');
disp('MOVIMIENTO DEL ROBOT: NO');
disp('==========================================');

carpeta_evidencia = fullfile(proyecto, 'entrega_avance2', 'evidencias');
if ~exist(carpeta_evidencia, 'dir')
    mkdir(carpeta_evidencia);
end

tabla = array2table([casos, salidas], 'VariableNames', ...
    {'error_distancia_m', 'error_angular_grados', ...
     'velocidad_lineal_m_s', 'velocidad_angular_rad_s'});

writetable(tabla, fullfile(carpeta_evidencia, 'fase1_salidas_matlab_real.csv'));
