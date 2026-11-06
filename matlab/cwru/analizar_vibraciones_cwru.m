%% ETAPA 1.5 - ANALISIS DE VIBRACIONES CWRU
% Proyecto: AGV de mantenimiento predictivo
% Comparacion temporal de cuatro condiciones de rodamiento

clear; clc; close all;

% Ubicacion del proyecto en Windows mediante WSL
proyecto = '\\wsl$\Ubuntu-22.04\home\diego\agv_predictivo';

carpetaDatos = fullfile(proyecto, 'datos', 'cwru');
carpetaResultados = fullfile(proyecto, 'resultados', ...
    'avance1', 'vibraciones');

if ~exist(carpetaResultados, 'dir')
    mkdir(carpetaResultados);
end

% Configuracion de los archivos CWRU
archivos = {'97.mat', '105.mat', '118.mat', '130.mat'};

variables = {'X097_DE_time', 'X105_DE_time', ...
             'X118_DE_time', 'X130_DE_time'};

nombres = {'Normal', 'Falla pista interna', ...
           'Falla bola', 'Falla pista externa'};

% Frecuencias de muestreo originales (Hz)
fs = [48000, 12000, 12000, 12000];

% Figura de comparacion temporal
fig = figure('Name', 'Vibraciones CWRU', ...
    'Color', 'w', 'Position', [100 100 1100 750]);

for k = 1:numel(archivos)

    ruta = fullfile(carpetaDatos, archivos{k});

    if ~isfile(ruta)
        error('No se encontro el archivo: %s', ruta);
    end

    datos = load(ruta, variables{k});

    % Canal DE: acelerometro del extremo de accionamiento
    x = double(datos.(variables{k}));
    x = x(:);

    % Mostrar los primeros 0.2 segundos
    duracion = 0.2;
    N = min(numel(x), round(duracion * fs(k)));

    t = (0:N-1)' / fs(k);

    subplot(4,1,k);
    plot(t, x(1:N), 'LineWidth', 0.8);
    grid on;

    title(sprintf('%s - %s', nombres{k}, archivos{k}));
    xlabel('Tiempo (s)');
    ylabel('Aceleracion (g)');

    fprintf('%s: %d muestras, Fs = %d Hz\n', ...
        nombres{k}, numel(x), fs(k));
end

sgtitle('Comparacion temporal de vibraciones CWRU');

% Guardar la figura como evidencia
archivoFigura = fullfile(carpetaResultados, ...
    'comparacion_temporal_cwru.png');

exportgraphics(fig, archivoFigura, 'Resolution', 200);

fprintf('\nFigura guardada en:\n%s\n', archivoFigura);
