
%% EXPORTACION CORREGIDA PARA NAV2
clear; clc; close all;

load('mapa_industrial.mat');

carpeta = fullfile('..','mapas');
if ~exist(carpeta,'dir')
    mkdir(carpeta);
end

%% Geometria
paso = 1/resolucion;
[X,Y] = meshgrid(x,y);

ocupacion = false(size(X));

radio_maquina = 0.20;
espesor_placa = 0.025;
ancho_placa = 0.50;

for i = 1:height(estaciones)

    % Interseccion conservadora cilindro-celda
    dx = max(abs(X-estaciones.x_maquina(i))-paso/2,0);
    dy = max(abs(Y-estaciones.y_maquina(i))-paso/2,0);

    maquina = dx.^2 + dy.^2 <= radio_maquina^2;

    % Interseccion rectangulo-celda
    placa = ...
        abs(X-estaciones.x_placa(i)) <= ...
        espesor_placa/2 + paso/2 & ...
        abs(Y-estaciones.y_placa(i)) <= ...
        ancho_placa/2 + paso/2;

    ocupacion = ocupacion | maquina | placa;
end

%% Crear imagen
% Libre = 254
% Ocupado = 0
imagen = uint8(~ocupacion)*254;

% Primera fila de imagen corresponde al norte
imagen = flipud(imagen);

imwrite(imagen,fullfile(carpeta, ...
    'planta_industrial.pgm'));

%% Crear YAML
fid = fopen(fullfile(carpeta, ...
    'planta_industrial.yaml'),'w');

assert(fid ~= -1,'Error al crear YAML');

fprintf(fid,'image: planta_industrial.pgm\n');
fprintf(fid,'mode: trinary\n');
fprintf(fid,'resolution: %.4f\n',paso);
fprintf(fid,'origin: [-2.5, -2.0, 0.0]\n');
fprintf(fid,'negate: 0\n');
fprintf(fid,'occupied_thresh: 0.65\n');
fprintf(fid,'free_thresh: 0.25\n');

fclose(fid);

%% Visualizar
figure;
imagesc(x,y,double(ocupacion));
set(gca,'YDir','normal');
axis equal;
axis([-2.5 2.5 -2 2]);
grid on;

colormap([1 1 1; 0 0 0]);

title('Mapa industrial corregido para Nav2');
xlabel('X (m)');
ylabel('Y (m)');

disp('Exportacion Nav2 corregida.');
