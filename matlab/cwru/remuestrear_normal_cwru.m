%% ETAPA 1.5 - REMUESTREO DE SENAL NORMAL CWRU
% Proyecto: AGV de mantenimiento predictivo
% Convertir 97.mat de 48000 Hz a 12000 Hz

clear;
clc;
close all;

%% 1. RUTAS

proyecto = '\\wsl$\Ubuntu-22.04\home\diego\agv_predictivo';

carpetaDatos = fullfile(proyecto, 'datos', 'cwru');

carpetaResultados = fullfile(proyecto, ...
    'resultados', 'avance1', 'vibraciones');

if ~exist(carpetaResultados, 'dir')
    mkdir(carpetaResultados);
end

%% 2. CARGAR SENAL ORIGINAL

rutaOriginal = fullfile(carpetaDatos, '97.mat');

datos = load(rutaOriginal, 'X097_DE_time');

xOriginal = double(datos.X097_DE_time(:));

fsOriginal = 48000;
fsNueva = 12000;

fprintf('Muestras originales: %d\n', numel(xOriginal));
fprintf('Frecuencia original: %d Hz\n', fsOriginal);

%% 3. REMUESTREAR CON FILTRO ANTIALIASING

% Relacion 12000 / 48000 = 1 / 4
xRemuestreada = resample(xOriginal, 1, 4);

fprintf('Muestras remuestreadas: %d\n', numel(xRemuestreada));
fprintf('Frecuencia nueva: %d Hz\n', fsNueva);

%% 4. COMPARAR INDICADORES RMS

rmsOriginal = sqrt(mean(xOriginal.^2));
rmsRemuestreado = sqrt(mean(xRemuestreada.^2));

fprintf('\nRMS original: %.6f g\n', rmsOriginal);
fprintf('RMS remuestreado: %.6f g\n', rmsRemuestreado);

%% 5. COMPARACION TEMPORAL

duracion = 0.2;

N1 = min(numel(xOriginal), round(duracion * fsOriginal));
N2 = min(numel(xRemuestreada), round(duracion * fsNueva));

t1 = (0:N1-1)' / fsOriginal;
t2 = (0:N2-1)' / fsNueva;

fig = figure('Name', 'Remuestreo CWRU', ...
    'Color', 'w', 'Position', [100 100 1100 650]);

subplot(2,1,1);
plot(t1, xOriginal(1:N1), 'b');
grid on;
title('Senal normal original - 48 kHz');
xlabel('Tiempo (s)');
ylabel('Aceleracion (g)');

subplot(2,1,2);
plot(t2, xRemuestreada(1:N2), 'r');
grid on;
title('Senal normal remuestreada - 12 kHz');
xlabel('Tiempo (s)');
ylabel('Aceleracion (g)');

sgtitle('Comparacion antes y despues del remuestreo');

%% 6. GUARDAR SENAL REMUESTREADA

% Nombre de variable para analisis posterior
X097_DE_time_12k = xRemuestreada;

rutaMAT = fullfile(carpetaDatos, '97_12k.mat');

save(rutaMAT, 'X097_DE_time_12k', ...
    'fsNueva', 'fsOriginal', '-v7');

%% 7. GUARDAR FIGURA

rutaFigura = fullfile(carpetaResultados, ...
    'remuestreo_normal_48k_a_12k.png');

exportgraphics(fig, rutaFigura, 'Resolution', 200);

%% 8. GUARDAR TABLA DE COMPARACION

tipo = {'Original'; 'Remuestreada'};
frecuenciaHz = [fsOriginal; fsNueva];
numeroMuestras = [numel(xOriginal); numel(xRemuestreada)];
RMS_g = [rmsOriginal; rmsRemuestreado];

tabla = table(tipo, frecuenciaHz, numeroMuestras, RMS_g, ...
    'VariableNames', ...
    {'Tipo', 'Frecuencia_Hz', 'Muestras', 'RMS_g'});

disp(tabla);

rutaCSV = fullfile(carpetaResultados, ...
    'comparacion_remuestreo_cwru.csv');

writetable(tabla, rutaCSV);

fprintf('\nREMUESTREO COMPLETADO\n');
fprintf('MAT: %s\n', rutaMAT);
fprintf('Figura: %s\n', rutaFigura);
fprintf('CSV: %s\n', rutaCSV);
