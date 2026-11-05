
%% TAREA 1.3 - VALIDACION DE RUTAS
clear; clc; close all;

%% Cargar mapa y datos
load('mapa_industrial.mat');

carpeta = fullfile('..','datos');

D = readtable(fullfile(carpeta, ...
    'matriz_distancias.csv'));

disp('MATRIZ DE DISTANCIAS:');
disp(D);

%% Puntos esperados
puntos = [
    -1.8000,  0.00;
    0.9015, -1.40;
    0.9015, -0.70;
    0.9015,  0.00;
    0.9015,  0.70;
    0.9015,  1.40
    ];

nombres = ["Base","E1","E2","E3","E4","E5"];

%% Comprobar las cinco rutas desde la base
fprintf('\nVALIDACION DE RUTAS:\n');

for j = 2:6

    archivo = sprintf('ruta_Base_%s.csv', ...
        char(nombres(j)));

    ruta = readtable(fullfile(carpeta,archivo));

    coordenadas = [ruta.x ruta.y];

    inicio = coordenadas(1,:);
    destino = coordenadas(end,:);

    error_inicio = norm(inicio-puntos(1,:));
    error_destino = norm(destino-puntos(j,:));

    segmentos = diff(coordenadas,1,1);
    longitud = sum(vecnorm(segmentos,2,2));

    % Muestreo de segmentos para detectar colisiones
    colision = false;

    for k = 1:size(coordenadas,1)-1
        a = coordenadas(k,:);
        b = coordenadas(k+1,:);

        n = max(2,ceil(norm(b-a)*resolucion*4)+1);

        for t = linspace(0,1,n)
            p = a + t*(b-a);

            if p(1)<min(x) || p(1)>max(x) || ...
                    p(2)<min(y) || p(2)>max(y)
                colision = true;
                continue
            end

            [~,ix] = min(abs(x-p(1)));
            [~,iy] = min(abs(y-p(2)));

            if inflado(iy,ix)
                colision = true;
            end
        end
    end

    fprintf('\n%s:\n',nombres(j));
    fprintf('Longitud: %.3f m\n',longitud);
    fprintf('Error inicial: %.6f m\n',error_inicio);
    fprintf('Error final: %.6f m\n',error_destino);

    if colision
        fprintf('Estado: REVISAR COLISION\n');
    else
        fprintf('Estado: SIN COLISION DETECTADA\n');
    end

end
