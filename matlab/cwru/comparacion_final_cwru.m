%% ETAPA 1.5 - COMPARACION FINAL CWRU A 12 kHz
clear; clc; close all;

proyecto = '\\wsl$\Ubuntu-22.04\home\diego\agv_predictivo';
carpetaDatos = fullfile(proyecto, 'datos', 'cwru');
carpetaResultados = fullfile(proyecto, ...
    'resultados', 'avance1', 'vibraciones');

archivos = {'97_12k.mat'; '105.mat'; '118.mat'; '130.mat'};

variables = {'X097_DE_time_12k'; 'X105_DE_time'; ...
             'X118_DE_time'; 'X130_DE_time'};

condiciones = {'Normal'; 'Pista interna'; ...
               'Bola'; 'Pista externa'};

fs = 12000;
n = numel(archivos);

RMS_g = zeros(n,1);
Pico_g = zeros(n,1);
FactorCresta = zeros(n,1);
Curtosis = zeros(n,1);

fig = figure('Name', 'Comparacion CWRU 12 kHz', ...
    'Color', 'w', 'Position', [100 100 1100 800]);

for k = 1:n
    datos = load(fullfile(carpetaDatos, archivos{k}), variables{k});
    x = double(datos.(variables{k}));
    x = x(:);

    RMS_g(k) = sqrt(mean(x.^2));
    Pico_g(k) = max(abs(x));
    FactorCresta(k) = Pico_g(k) / RMS_g(k);

    % Curtosis de Pearson: normal gaussiana ~ 3
    xc = x - mean(x);
    varianza = mean(xc.^2);
    Curtosis(k) = mean(xc.^4) / (varianza^2);

    % Espectro FFT
    N = numel(x);
    Y = fft(xc);
    P1 = abs(Y(1:floor(N/2)+1)) / N;

    if mod(N,2) == 0
        P1(2:end-1) = 2*P1(2:end-1);
    else
        P1(2:end) = 2*P1(2:end);
    end

    f = (0:floor(N/2))' * fs / N;

    subplot(4,1,k);
    plot(f, P1, 'LineWidth', 0.8);
    xlim([0 6000]);
    grid on;
    title(sprintf('%s - %s', condiciones{k}, archivos{k}));
    xlabel('Frecuencia (Hz)');
    ylabel('Amplitud (g)');
end

sgtitle('Comparacion FFT de rodamientos CWRU a 12 kHz');

tabla = table(archivos, condiciones, RMS_g, Pico_g, ...
    FactorCresta, Curtosis, ...
    'VariableNames', {'Archivo','Condicion','RMS_g', ...
    'Pico_g','FactorCresta','Curtosis'});

disp(tabla);

writetable(tabla, fullfile(carpetaResultados, ...
    'indicadores_finales_cwru_12k.csv'));

exportgraphics(fig, fullfile(carpetaResultados, ...
    'comparacion_final_fft_cwru_12k.png'), ...
    'Resolution', 200);

fprintf('\nCOMPARACION FINAL A 12 kHz COMPLETADA\n');
