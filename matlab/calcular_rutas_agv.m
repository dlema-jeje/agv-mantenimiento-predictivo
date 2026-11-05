
%% TAREA 1.3 - RUTAS DEL AGV CON DIJKSTRA
clear; clc; close all;

%% Cargar mapa de ocupacion ya generado
load('mapa_industrial.mat');

% Puntos: base + cinco estaciones
puntos = [
    -1.8000,  0.00;
     0.9015, -1.40;
     0.9015, -0.70;
     0.9015,  0.00;
     0.9015,  0.70;
     0.9015,  1.40
];

nombres = ["Base","E1","E2","E3","E4","E5"];
N = size(puntos,1);

%% Construir grafo de celdas libres
[filas,columnas] = size(inflado);
libres = find(~inflado);

ids = zeros(filas,columnas);
ids(libres) = 1:numel(libres);

% Vecindad de 8 direcciones
direcciones = [
     1, 0;
     0, 1;
     1, 1;
     1,-1
];

origenes = [];
destinos = [];
pesos = [];

for k = 1:size(direcciones,1)
    dr = direcciones(k,1);
    dc = direcciones(k,2);

    for r = 1:filas
        for c = 1:columnas
            r2 = r + dr;
            c2 = c + dc;

            if r2<1 || r2>filas || c2<1 || c2>columnas
                continue
            end

            if inflado(r,c) || inflado(r2,c2)
                continue
            end

            % Evitar cortar esquinas ocupadas
            if dr~=0 && dc~=0
                if inflado(r2,c) || inflado(r,c2)
                    continue
                end
            end

            origenes(end+1,1) = ids(r,c);
            destinos(end+1,1) = ids(r2,c2);

            pesos(end+1,1) = hypot(dr,dc)/resolucion;
        end
    end
end

G = graph(origenes,destinos,pesos,numel(libres));

%% Asociar puntos a celdas
nodos = zeros(N,1);

for i = 1:N
    [~,c] = min(abs(x-puntos(i,1)));
    [~,r] = min(abs(y-puntos(i,2)));

    if inflado(r,c)
        error('El punto %s esta ocupado.',nombres(i));
    end

    nodos(i) = ids(r,c);
end

%% Matriz de distancias y rutas
D = zeros(N,N);
rutas = cell(N,N);

for i = 1:N
    for j = 1:N
        if i == j
            rutas{i,j} = puntos(i,:);
            continue
        end

        [camino,distancia] = shortestpath( ...
            G,nodos(i),nodos(j));

        if isempty(camino)
            error('No hay ruta entre %s y %s', ...
                nombres(i),nombres(j));
        end

        [rr,cc] = ind2sub( ...
            size(inflado),libres(camino));

        ruta = [x(cc(:))', y(rr(:))'];
        ruta = reshape(ruta,[],2);

        % Conservar las coordenadas solicitadas
        ruta = [puntos(i,:); ruta; puntos(j,:)];

        rutas{i,j} = ruta;
        D(i,j) = distancia;
    end
end

%% Crear carpeta de exportacion
carpeta = fullfile('..','datos');

if ~exist(carpeta,'dir')
    mkdir(carpeta);
end

%% Exportar matriz de distancias
tabla = array2table(D, ...
    'VariableNames',cellstr(nombres));

tabla = addvars(tabla,nombres', ...
    'Before',1,'NewVariableNames','Origen');

writetable(tabla,fullfile(carpeta, ...
    'matriz_distancias.csv'));

%% Exportar todos los tramos
for i = 1:N
    for j = 1:N
        if i == j
            continue
        end

        ruta = rutas{i,j};

        T = array2table(ruta, ...
            'VariableNames',{'x','y'});

        archivo = sprintf('ruta_%s_%s.csv', ...
            char(nombres(i)),char(nombres(j)));

        writetable(T,fullfile(carpeta,archivo));
    end
end

%% Visualizar rutas desde la base
figure('Name','Rutas AGV - Dijkstra');
imagesc(x,y,double(inflado));
set(gca,'YDir','normal');
axis equal;
axis([-2.5 2.5 -2 2]);
hold on; grid on;

colormap([1 1 1; 0.3 0.35 0.4]);

colores = lines(5);

for j = 2:N
    ruta = rutas{1,j};

    plot(ruta(:,1),ruta(:,2), ...
        'LineWidth',1.7, ...
        'Color',colores(j-1,:));
end

plot(puntos(1,1),puntos(1,2),'kp', ...
    'MarkerSize',14,'MarkerFaceColor','y');

plot(puntos(2:end,1),puntos(2:end,2), ...
    'g*','MarkerSize',10);

for i = 1:N
    text(puntos(i,1)+0.08,puntos(i,2), ...
        nombres(i),'FontWeight','bold');
end

title('Rutas de inspeccion - Dijkstra');
xlabel('X (m)');
ylabel('Y (m)');

exportgraphics(gcf,fullfile(carpeta, ...
    'rutas_dijkstra.png'),'Resolution',200);

disp('MATRIZ DE DISTANCIAS (m):');
disp(tabla);

disp('Rutas y matriz exportadas a datos/');
