
%% AVANCE 2 - VALIDACION INICIAL DEL CONTROLADOR DIFUSO
% Proyecto: AGV de mantenimiento predictivo
% Objetivo: comprobar la coherencia de las salidas Mamdani

clear;
clc;
close all;

%% 1. RUTAS DEL PROYECTO

proyecto = '\\wsl$\Ubuntu-22.04\home\diego\agv_predictivo';

carpetaDifuso = fullfile(proyecto,'matlab','difuso');

carpetaResultados = fullfile(proyecto,'resultados', ...
    'avance2','validacion');

if ~exist(carpetaResultados,'dir')
    mkdir(carpetaResultados);
end

%% 2. CARGAR CONTROLADOR

rutaFIS = fullfile(carpetaDifuso,'acople_agv.fis');

if ~isfile(rutaFIS)
    error('No se encontro el archivo acople_agv.fis');
end

fis = readfis(rutaFIS);

fprintf('CONTROLADOR CARGADO: %s\n',fis.Name);
fprintf('Entradas: %d\n',numel(fis.Inputs));
fprintf('Salidas: %d\n',numel(fis.Outputs));
fprintf('Reglas: %d\n',numel(fis.Rules));

assert(numel(fis.Rules)==25, ...
    'El controlador debe contener 25 reglas.');

%% 3. DEFINIR DIEZ CASOS DE PRUEBA

% Columna 1: error de distancia en metros
% Columna 2: error angular en grados

pruebas = [
     0.35,   0;
     0.15,   0;
     0.04,   0;
     0.00,   0;
    -0.03,   0;
     0.15,  12;
     0.15, -12;
     0.04,  18;
     0.04, -18;
     0.00,   3
];

%% 4. EVALUAR EL CONTROLADOR

salidas = evalfis(fis,pruebas);

velocidadLineal = salidas(:,1);
velocidadAngular = salidas(:,2);

%% 5. COMPROBACIONES NUMERICAS

assert(all(isfinite(salidas),'all'), ...
    'Se encontraron salidas no finitas.');

assert(all(velocidadLineal >= -0.05-1e-9) && ...
       all(velocidadLineal <= 0.15+1e-9), ...
       'Velocidad lineal fuera del rango.');

assert(all(velocidadAngular >= -0.8-1e-9) && ...
       all(velocidadAngular <= 0.8+1e-9), ...
       'Velocidad angular fuera del rango.');

fprintf('\nLas diez evaluaciones son finitas y estan dentro de los rangos.\n');

%% 6. CREAR TABLA DE RESULTADOS

caso = (1:size(pruebas,1))';

resultados = table( ...
    caso, ...
    pruebas(:,1), ...
    pruebas(:,2), ...
    velocidadLineal, ...
    velocidadAngular, ...
    'VariableNames',{ ...
        'Caso', ...
        'ErrorDistancia_m', ...
        'ErrorAngular_deg', ...
        'VelocidadLineal_m_s', ...
        'VelocidadAngular_rad_s'});

disp('===== RESULTADOS DE LAS DIEZ PRUEBAS =====');
disp(resultados);

%% 7. GUARDAR CSV

rutaCSV = fullfile(carpetaResultados, ...
    'pruebas_controlador_mamdani.csv');

writetable(resultados,rutaCSV);

fprintf('\nTabla guardada en:\n%s\n',rutaCSV);

%% 8. GRAFICAR RESPUESTAS

fig = figure('Name','Pruebas controlador Mamdani', ...
    'Color','w','Position',[100 100 1100 650]);

subplot(2,1,1);
bar(caso,velocidadLineal);
grid on;
ylabel('Velocidad lineal (m/s)');
title('Salida lineal en los diez casos');
xticks(caso);

subplot(2,1,2);
bar(caso,velocidadAngular);
grid on;
xlabel('Caso de prueba');
ylabel('Velocidad angular (rad/s)');
title('Salida angular en los diez casos');
xticks(caso);

sgtitle('Avance 2 - Validacion inicial del controlador');

rutaFigura = fullfile(carpetaResultados, ...
    'pruebas_controlador_mamdani.png');

exportgraphics(fig,rutaFigura,'Resolution',200);

fprintf('\nFigura guardada en:\n%s\n',rutaFigura);

fprintf('\nVALIDACION NUMERICA INICIAL COMPLETADA.\n');
