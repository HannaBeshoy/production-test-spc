% course_methods.m - the Applied Statistics course's methods in MATLAB, on the same data
% as the Python analysis (analyse.py). Runs in MATLAB and in GNU Octave without any toolbox:
% the p-values come from betainc and gammainc. With the Statistics and Machine Learning
% Toolbox, the one-line equivalent of each test is given in a comment.
%
%   cd matlab; course_methods            % prints the results, writes ../results/matlab_check.txt
%
% Data (written by tools/export_data.py):
%   ../data/matlab/leak.csv         day (1 = Mon ... 5 = Fri), time in production days, leak rate (sccm)
%   ../data/matlab/shift_table.csv  rows shift A, B; columns FAIL, PASS (first attempts)
%   ../data/matlab/eol2.csv         current (A), stroke (mm) of the same test run
function course_methods
    here = fileparts(mfilename('fullpath'));
    leak  = load_csv(fullfile(here, '..', 'data', 'matlab', 'leak.csv'));
    shift = load_csv(fullfile(here, '..', 'data', 'matlab', 'shift_table.csv'));
    eol   = load_csv(fullfile(here, '..', 'data', 'matlab', 'eol2.csv'));
    day = leak(:, 1); t = leak(:, 2); y = leak(:, 3);
    a = y(day <= 2);                 % Monday-Tuesday: before the wear
    b = y(day >= 4);                 % Thursday-Friday
    R = struct();

    % ---- Lecture 7: sample statistics and a confidence interval of the mean
    n = numel(a); m = mean(a); s = std(a);
    half = t_inv(0.975, n - 1) * s / sqrt(n);
    R.mean_a = m; R.sd_a = s; R.ci_lo = m - half; R.ci_hi = m + half;
    fprintf('Mon-Tue leak rate: n = %d, mean %.4f, SD %.4f, 95 %% CI [%.4f, %.4f]\n', n, m, s, m - half, m + half);

    % ---- Lecture 8: two-sample t-test with unequal variances (Welch)
    % toolbox: [h, p, ci, stats] = ttest2(b, a, 'Vartype', 'unequal')
    va = var(a) / numel(a); vb = var(b) / numel(b);
    tw = (mean(b) - mean(a)) / sqrt(va + vb);
    df = (va + vb)^2 / (va^2 / (numel(a) - 1) + vb^2 / (numel(b) - 1));
    R.welch_t = tw; R.welch_df = df; R.welch_p = t_p2(tw, df);
    fprintf('Welch t-test Thu-Fri vs Mon-Tue: t = %.4f, df = %.2f, p = %.3g\n', tw, df, R.welch_p);

    % ---- Lecture 9: chi-square goodness of fit (normal, 6 classes of equal probability)
    % toolbox: [h, p, st] = chi2gof(a, 'Edges', [-Inf edges Inf], 'NParams', 2)
    k = 6;
    edges = m + s * norm_inv((1:k - 1) / k);
    obs = histc(a, [-Inf, edges, Inf]); obs = obs(1:k);   %#ok<HISTC> works in MATLAB and Octave
    ex = n / k;
    R.gof_chi2 = sum((obs - ex).^2 / ex); R.gof_p = chi2_sf(R.gof_chi2, k - 3);
    fprintf('Chi-square goodness of fit (normal): chi2 = %.4f, df = %d, p = %.4f\n', R.gof_chi2, k - 3, R.gof_p);

    % ---- Lecture 9: chi-square test of independence, shift x result
    % toolbox: [tbl, chi2, p] = crosstab(shift_of_run, result_of_run)
    E = sum(shift, 2) * sum(shift, 1) / sum(shift(:));
    R.shift_chi2 = sum(sum((shift - E).^2 ./ E)); R.shift_p = chi2_sf(R.shift_chi2, 1);
    fprintf('Chi-square independence, shift x result: chi2 = %.4f, df = 1, p = %.4f\n', R.shift_chi2, R.shift_p);

    % ---- Lecture 10: correlation and linear regression
    % toolbox: [r, p] = corr(eol(:,1), eol(:,2));   mdl = fitlm(t(sel), y(sel))
    c = corrcoef(eol(:, 1), eol(:, 2)); R.pearson_r = c(1, 2);
    fprintf('Correlation current vs stroke: r = %.4f\n', R.pearson_r);
    sel = t >= 1.5;                               % the rising part, from the change point of analyse.py
    x = t(sel); yy = y(sel); nr = numel(x);
    p = polyfit(x, yy, 1);                        % yy = p(1) * x + p(2)
    res = yy - polyval(p, x);
    se_b = sqrt(sum(res.^2) / (nr - 2)) / sqrt(sum((x - mean(x)).^2));
    R.slope = p(1); R.slope_se = se_b; R.r2 = 1 - sum(res.^2) / sum((yy - mean(yy)).^2);
    R.slope_p = t_p2(p(1) / se_b, nr - 2);
    fprintf('Regression of the rising part: slope %.4f sccm/day (SE %.4f), R^2 = %.4f, p = %.3g\n', ...
            R.slope, se_b, R.r2, R.slope_p);

    % ---- Lecture 11: one-way ANOVA, leak rate by day
    % toolbox: [p, tbl] = anova1(y, day)
    grand = mean(y); ssb = 0; ssw = 0;
    for d = 1:5
        g = y(day == d);
        ssb = ssb + numel(g) * (mean(g) - grand)^2;
        ssw = ssw + sum((g - mean(g)).^2);
    end
    N = numel(y);
    R.anova_F = (ssb / 4) / (ssw / (N - 5)); R.anova_p = f_sf(R.anova_F, 4, N - 5);
    R.eta2 = ssb / (ssb + ssw);
    fprintf('One-way ANOVA by day: F(4, %d) = %.4f, p = %.3g, eta^2 = %.4f\n', N - 5, R.anova_F, R.anova_p, R.eta2);

    % ---- results for the comparison with Python (tests/test_matlab.py)
    f = fopen(fullfile(here, '..', 'results', 'matlab_check.txt'), 'w');
    names = fieldnames(R);
    for i = 1:numel(names)
        fprintf(f, '%s %.12g\n', names{i}, R.(names{i}));
    end
    fclose(f);
end

% ---------------------------------------------------------------- helpers
function M = load_csv(path)
    M = dlmread(path, ',');           %#ok<DLMRD> numbers only; same call in MATLAB and Octave
end

function p = t_p2(t, v)               % two-sided p-value of a t statistic, from the incomplete beta
    p = betainc(v ./ (v + t.^2), v / 2, 0.5);   % computed as a tail, so tiny p-values do not round to 0
end

function t = t_inv(p, v)              % t quantile by bisection (p > 0.5)
    lo = 0; hi = 1000;
    for i = 1:200
        t = (lo + hi) / 2;
        if 1 - t_p2(t, v) / 2 < p, lo = t; else, hi = t; end
    end
end

function p = chi2_sf(x, v)            % upper tail of the chi-square distribution = incomplete gamma
    p = gammainc(x / 2, v / 2, 'upper');
end

function p = f_sf(x, d1, d2)          % upper tail of the F distribution, from the incomplete beta
    p = betainc(d2 ./ (d2 + d1 * x), d2 / 2, d1 / 2);
end

function z = norm_inv(p)              % standard normal quantile
    z = -sqrt(2) * erfcinv(2 * p);
end
