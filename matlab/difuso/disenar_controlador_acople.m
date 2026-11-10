
%% AVANCE 2 - FUNCIONES DE MEMBRESIA DEL CONTROLADOR
clear; clc; close all;

proyecto = '\\wsl$\Ubuntu-22.04\home\diego\agv_predictivo';
carpeta = fullfile(proyecto, 'matlab', 'difuso');
cd(carpeta);

fis = mamfis('Name','AcopleAGV', ...
    'AndMethod','min', ...
    'OrMethod','max', ...
    'ImplicationMethod','min', ...
    'AggregationMethod','max', ...
    'DefuzzificationMethod','centroid');

%% ENTRADA 1: ERROR DE DISTANCIA (m)
fis = addInput(fis,[-0.05 0.45],'Name','ErrorDistancia');

fis = addMF(fis,'ErrorDistancia','trapmf', ...
    [-0.05 -0.05 -0.03 -0.005],'Name','Pasado');

fis = addMF(fis,'ErrorDistancia','trimf', ...
    [-0.015 0 0.015],'Name','Acoplado');

fis = addMF(fis,'ErrorDistancia','trimf', ...
    [0.005 0.04 0.09],'Name','MuyCerca');

fis = addMF(fis,'ErrorDistancia','trimf', ...
    [0.06 0.15 0.28],'Name','Cerca');

fis = addMF(fis,'ErrorDistancia','trapmf', ...
    [0.22 0.32 0.45 0.45],'Name','Lejos');

%% ENTRADA 2: ERROR ANGULAR (grados)
fis = addInput(fis,[-20 20],'Name','ErrorAngular');

fis = addMF(fis,'ErrorAngular','trapmf', ...
    [-20 -20 -15 -8],'Name','NegGrande');

fis = addMF(fis,'ErrorAngular','trimf', ...
    [-15 -7 0],'Name','NegPequeno');

fis = addMF(fis,'ErrorAngular','trimf', ...
    [-5 0 5],'Name','Cero');

fis = addMF(fis,'ErrorAngular','trimf', ...
    [0 7 15],'Name','PosPequeno');

fis = addMF(fis,'ErrorAngular','trapmf', ...
    [8 15 20 20],'Name','PosGrande');

%% SALIDA 1: VELOCIDAD LINEAL (m/s)
fis = addOutput(fis,[-0.05 0.15],'Name','VelocidadLineal');

fis = addMF(fis,'VelocidadLineal','trapmf', ...
    [-0.05 -0.05 -0.035 -0.005],'Name','Retroceso');

fis = addMF(fis,'VelocidadLineal','trimf', ...
    [-0.01 0 0.01],'Name','Cero');

fis = addMF(fis,'VelocidadLineal','trimf', ...
    [0.005 0.025 0.05],'Name','MuyLenta');

fis = addMF(fis,'VelocidadLineal','trimf', ...
    [0.035 0.07 0.105],'Name','Lenta');

fis = addMF(fis,'VelocidadLineal','trapmf', ...
    [0.09 0.12 0.15 0.15],'Name','Media');

%% SALIDA 2: VELOCIDAD ANGULAR (rad/s)
fis = addOutput(fis,[-0.8 0.8],'Name','VelocidadAngular');

fis = addMF(fis,'VelocidadAngular','trapmf', ...
    [-0.8 -0.8 -0.65 -0.3],'Name','NegGrande');

fis = addMF(fis,'VelocidadAngular','trimf', ...
    [-0.55 -0.3 0],'Name','NegMedia');

fis = addMF(fis,'VelocidadAngular','trimf', ...
    [-0.1 0 0.1],'Name','Cero');

fis = addMF(fis,'VelocidadAngular','trimf', ...
    [0 0.3 0.55],'Name','PosMedia');

fis = addMF(fis,'VelocidadAngular','trapmf', ...
    [0.3 0.65 0.8 0.8],'Name','PosGrande');

%% REGLAS DIFUSAS - 25 COMBINACIONES

% Filas: Pasado, Acoplado, MuyCerca, Cerca, Lejos
% Columnas: NegGrande, NegPequeno, Cero,
%           PosPequeno, PosGrande
%
% Indices de velocidad lineal:
% 1 Retroceso, 2 Cero, 3 MuyLenta,
% 4 Lenta, 5 Media

tablaLineal = [
    1 1 1 1 1;
    2 2 2 2 2;
    2 3 3 3 2;
    3 4 4 4 3;
    3 4 5 4 3
    ];

% Indices de velocidad angular:
% 1 NegGrande, 2 NegMedia, 3 Cero,
% 4 PosMedia, 5 PosGrande
%
% Hipotesis inicial:
% signo de salida igual al signo del error.
% Se verificara antes de la prueba fisica.

tablaAngular = [1 2 3 4 5];

% Formato de addRule:
% [entrada1 entrada2 salida1 salida2 peso operador]
%
% operador 1 = AND

reglas = zeros(25,6);
contador = 0;

for i = 1:5
    for j = 1:5
        contador = contador + 1;

        reglas(contador,:) = [
            i, ...
            j, ...
            tablaLineal(i,j), ...
            tablaAngular(j), ...
            1, ...
            1
            ];
    end
end

fis = addRule(fis,reglas);

fprintf('\nReglas generadas: %d\n',numel(fis.Rules));

% Mostrar reglas en lenguaje legible
showrule(fis)

% Guardar controlador completo
writeFIS(fis,fullfile(carpeta,'acople_agv.fis'));

save(fullfile(carpeta,'controlador_completo.mat'),'fis');

%% VISUALIZACION DE LAS CUATRO VARIABLES
fig = figure('Name','Funciones de membresia AGV', ...
    'Color','w','Position',[100 100 1100 800]);

subplot(2,2,1); plotmf(fis,'input',1); grid on;
subplot(2,2,2); plotmf(fis,'input',2); grid on;
subplot(2,2,3); plotmf(fis,'output',1); grid on;
subplot(2,2,4); plotmf(fis,'output',2); grid on;

sgtitle('Avance 2 - Funciones de membresia del AGV');

exportgraphics(fig,fullfile(proyecto,'resultados', ...
    'avance2','diseno','funciones_membresia.png'), ...
    'Resolution',200);

save(fullfile(carpeta,'controlador_membresias.mat'),'fis');

fprintf('\nEntradas: %d\n',numel(fis.Inputs));
fprintf('Salidas: %d\n',numel(fis.Outputs));
fprintf('Reglas actuales: %d\n',numel(fis.Rules));
