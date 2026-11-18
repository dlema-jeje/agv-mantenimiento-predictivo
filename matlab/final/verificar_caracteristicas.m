function verificar_caracteristicas()
% Desde MATLAB: addpath('matlab/final'); verificar_caracteristicas
raiz = fileparts(fileparts(fileparts(mfilename('fullpath'))));
datos = fullfile(raiz, 'datos', 'final');
X = readmatrix(fullfile(datos, 'paridad_ventanas.csv'));
referencia = readmatrix(fullfile(datos, 'paridad_python.csv'));
assert(isequal(size(X), [5 2048]));
N = size(X, 2);
f = (0:N/2) * (12000/N);
Y = zeros(size(referencia));
for i = 1:size(X, 1)
    x = X(i, :);
    centrada = x - mean(x);
    v = mean(centrada.^2);
    r = sqrt(mean(x.^2));
    p = max(abs(x));
    P = abs(fft(x) / N).^2;
    P = P(1:N/2+1);
    P(2:end-1) = 2*P(2:end-1);
    % Momentos centrales poblacionales. Equivalen a kurtosis(x,1) y skewness(x,1).
    Y(i, :) = [r, p, mean(centrada.^4)/v^2, mean(centrada.^3)/v^1.5, ...
        std(x, 0), p/r, sum(P(f < 1000)), sum(P(f >= 1000 & f < 3000)), ...
        sum(P(f >= 3000))];
end
error_pct = 100 * abs(Y - referencia) ./ max(abs(referencia), 1e-12);
res = fullfile(raiz, 'resultados', 'final');
writematrix(Y, fullfile(res, 'paridad_matlab.csv'));
writematrix(error_pct, fullfile(res, 'paridad_error_matlab_pct.csv'));
fprintf('Máxima diferencia relativa: %.12g %%\n', max(error_pct(:)));
assert(all(error_pct(:) < 0.1), 'Se excedió la diferencia relativa del 0,1 %%');
end
