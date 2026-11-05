
%% PASO 1.3 - MAPA DE OCUPACION INDUSTRIAL
clear; clc; close all;

%% 1. Leer coordenadas de las estaciones
estaciones = readtable('estaciones.csv');

%% 2. Parametros del entorno
ancho = 5;
alto = 4;
resolucion = 20; % celdas por metro

x = -ancho/2 + 1/(2*resolucion) : ...
    1/resolucion : ancho/2;

y = -alto/2 + 1/(2*resolucion) : ...
    1/resolucion : alto/2;

[X,Y] = meshgrid(x,y);

%% 3. Crear mapa de ocupacion
ocupado = false(size(X));

radio_maquina = 0.20;
espesor_placa = 0.025;
ancho_placa = 0.50;

for i = 1:height(estaciones)

    % Maquina cilindrica
    dx = X - estaciones.x_maquina(i);
    dy = Y - estaciones.y_maquina(i);

    maquina = dx.^2 + dy.^2 <= radio_maquina^2;

    % Placa rectangular vertical, vista desde arriba
    placa = ...
        abs(X - estaciones.x_placa(i)) <= espesor_placa/2 & ...
        abs(Y - estaciones.y_placa(i)) <= ancho_placa/2;

    ocupado = ocupado | maquina | placa;
end

%% 4. Inflacion de obstaculos
margen_seguridad = 0.22;

radio_celdas = ceil(margen_seguridad*resolucion);
[DX,DY] = meshgrid(-radio_celdas:radio_celdas);

estructura = (DX.^2 + DY.^2) <= ...
    (margen_seguridad*resolucion)^2;

% Inflacion mediante convolucion, sin Image Processing Toolbox
inflado = conv2(double(ocupado), ...
                double(estructura), 'same') > 0;

%% 5. Visualizacion
figure('Name','Mapa industrial AGV');

imagesc(x,y,double(inflado));
set(gca,'YDir','normal');
axis equal;
axis([-2.5 2.5 -2 2]);
grid on;
hold on;

colormap([1 1 1; 0.25 0.3 0.35]);

% Obstaculos originales
contour(X,Y,double(ocupado),[0.5 0.5], ...
    'Color',[0.9 0.35 0.1], ...
    'LineWidth',1.5);

% Puntos de aproximacion
plot(estaciones.x_aproximacion, ...
     estaciones.y_aproximacion, ...
     'g*','MarkerSize',9,'LineWidth',1.5);

xlabel('X (m)');
ylabel('Y (m)');
title('Mapa de ocupacion industrial - AGV predictivo');

%% 6. Verificar puntos de aproximacion
fprintf('\nVALIDACION DE PUNTOS:\n');

for i = 1:height(estaciones)
    [~,ix] = min(abs(x-estaciones.x_aproximacion(i)));
    [~,iy] = min(abs(y-estaciones.y_aproximacion(i)));

    if inflado(iy,ix)
        fprintf('Estacion %d: OCUPADA\n',i);
    else
        fprintf('Estacion %d: LIBRE\n',i);
    end
end

%% 7. Guardar resultados
save('mapa_industrial.mat', ...
     'ocupado','inflado','x','y','resolucion','estaciones');

exportgraphics(gcf,'mapa_industrial.png','Resolution',200);

disp('Mapa industrial generado correctamente.');

