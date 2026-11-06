%% =========================================================
% ETAPA 1.5 - ANALISIS DE VIBRACIONES CWRU
% Proyecto: AGV de mantenimiento predictivo
%
% Analisis:
%   1. Carga de señales de vibracion
%   2. Calculo de RMS
%   3. Calculo del pico maximo
%   4. Calculo del factor de cresta
%   5. Transformada rapida de Fourier (FFT)
%   6. Exportacion de resultados
%% =========================================================

clear;
clc;
close all;

%% 1. RUTAS DEL PROYECTO

proyecto = '\\wsl$\Ubuntu-22.04\home\diego\agv_predictivo';

carpetaDatos = fullfile(proyecto, 'datos', 'cwru');

carpetaResultados = fullfile(proyecto, ...
    'resultados', 'avance1', 'vibraciones');

if ~exist(carpetaResultados, 'dir')
    mkdir(carpetaResultados);
end

%% 2. CONFIGURACION DE LOS ARCHIVOS CWRU

archivos = {
    '97.mat'
    '105.mat'
    '118.mat'
    '130.mat'
};

variables = {
    'X097_DE_time'
    'X105_DE_time'
    'X118_DE_time'
    'X130_DE_time'
};

condiciones = {
    'Normal'
    'Pista interna'
    'Bola'
    'Pista externa'
};

% Frecuencias de muestreo originales
fs = [48000; 12000; 12000; 12000];

numeroSenales = numel(archivos);

%% 3. PREPARAR TABLAS DE RESULTADOS

rmsValores = zeros(numeroSenales, 1);
picos = zeros(numeroSenales, 1);
factoresCresta = zeros(numeroSenales, 1);
frecuenciasDominantes = zeros(numeroSenales, 1);

%% 4. CREAR FIGURA PARA LOS ESPECTROS FFT

fig = figure( ...
    'Name', 'Analisis FFT CWRU', ...
    'Color', 'w', ...
    'Position', [100 100 1100 800]);

%% 5. PROCESAR LAS CUATRO SENALES

for k = 1:numeroSenales

    fprintf('\n====================================\n');
    fprintf('Procesando: %s\n', condiciones{k});
    fprintf('Archivo: %s\n', archivos{k});

    % Ruta completa del archivo
    ruta = fullfile(carpetaDatos, archivos{k});

    % Verificar existencia
    if ~isfile(ruta)
        error('No se encontro el archivo: %s', ruta);
    end

    % Cargar variable de vibracion DE
    datos = load(ruta, variables{k});

    x = double(datos.(variables{k}));
    x = x(:);

    N = numel(x);

    fprintf('Muestras: %d\n', N);
    fprintf('Frecuencia de muestreo: %d Hz\n', fs(k));

    %% 5.1 CALCULAR INDICADORES TEMPORALES

    % RMS
    rmsValores(k) = sqrt(mean(x.^2));

    % Pico maximo absoluto
    picos(k) = max(abs(x));

    % Factor de cresta
    if rmsValores(k) > 0
        factoresCresta(k) = picos(k) / rmsValores(k);
    else
        factoresCresta(k) = NaN;
    end

    %% 5.2 PREPARAR SENAL PARA FFT

    % Eliminar componente continua
    xFFT = x - mean(x);

    % Transformada rapida de Fourier
    Y = fft(xFFT);

    % Espectro de amplitud de dos lados
    P2 = abs(Y / N);

    % Espectro de amplitud de un lado
    P1 = P2(1:floor(N/2)+1);

    % Duplicar amplitudes interiores
    if mod(N,2) == 0
        if numel(P1) > 2
            P1(2:end-1) = 2 * P1(2:end-1);
        end
    else
        if numel(P1) > 1
            P1(2:end) = 2 * P1(2:end);
        end
    end

    % Eje de frecuencias
    f = (0:floor(N/2))' * fs(k) / N;

    %% 5.3 FRECUENCIA DOMINANTE EN 0-6000 Hz

    indices = find(f > 0 & f <= 6000);

    [~, indiceMaximo] = max(P1(indices));

    frecuenciasDominantes(k) = f(indices(indiceMaximo));

    %% 5.4 MOSTRAR ESPECTRO

    subplot(4,1,k);

    plot(f, P1, 'b', 'LineWidth', 0.8);

    grid on;
    xlim([0 6000]);

    title(sprintf('%s - %s', ...
        condiciones{k}, archivos{k}));

    xlabel('Frecuencia (Hz)');
    ylabel('Amplitud (g)');

    %% 5.5 MOSTRAR INDICADORES

    fprintf('RMS: %.6f g\n', rmsValores(k));
    fprintf('Pico: %.6f g\n', picos(k));
    fprintf('Factor de cresta: %.4f\n', factoresCresta(k));
    fprintf('Frecuencia dominante: %.2f Hz\n', ...
        frecuenciasDominantes(k));

end

%% 6. TITULO GENERAL

sgtitle('Comparacion de espectros FFT - CWRU');

%% 7. GUARDAR FIGURA

rutaFigura = fullfile(carpetaResultados, ...
    'comparacion_fft_cwru.png');

exportgraphics(fig, rutaFigura, 'Resolution', 200);

%% 8. CREAR TABLA DE RESULTADOS

resultados = table( ...
    archivos, ...
    condiciones, ...
    fs, ...
    rmsValores, ...
    picos, ...
    factoresCresta, ...
    frecuenciasDominantes, ...
    'VariableNames', { ...
        'Archivo', ...
        'Condicion', ...
        'Fs_Hz', ...
        'RMS_g', ...
        'Pico_g', ...
        'FactorCresta', ...
        'FrecuenciaDominante_Hz' ...
    });

%% 9. MOSTRAR TABLA

fprintf('\n====================================\n');
fprintf('RESUMEN DEL ANALISIS CWRU\n');
fprintf('====================================\n');

disp(resultados);

%% 10. EXPORTAR RESULTADOS A CSV

rutaCSV = fullfile(carpetaResultados, ...
    'indicadores_vibracion_cwru.csv');

writetable(resultados, rutaCSV);

%% 11. MENSAJE FINAL

fprintf('\nANALISIS FFT COMPLETADO\n');
fprintf('Figura guardada en:\n%s\n', rutaFigura);
fprintf('Tabla guardada en:\n%s\n', rutaCSV);
