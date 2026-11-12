# Project guide

## 1. The story in one paragraph

The leak tester LEAK-1 checks clutch release units. Its seal starts wearing on Wednesday, so every part reads a little leakier than it is. No part fails until Thursday afternoon, and the pass/fail counts only look bad on Friday. A control chart built from Monday-Tuesday data flags the shift on Wednesday morning. Everything else in the project either confirms that the shift is real (tests), measures it (intervals, regression, capability) or shows what does *not* matter (shift, torque, current vs stroke).

## 2. Control limits are not specification limits

| | Specification limits | Control limits |
| --- | --- | --- |
| come from | the customer / the drawing | the process's own variation (mean +- 3 sigma) |
| answer | is this part good? | has the process changed? |
| LEAK-1 | 2.0 sccm | 1.715 sccm (from Mon-Tue) |

A point above 1.715 but below 2.0 is a good part from a changed process. That is the early warning.

**Phase I / phase II.** Limits are computed from a period believed stable (Mon-Tue), then frozen. If you recompute the limits including the drifting days, they widen and swallow the drift.

**Sigma within, from the moving range.** sigma = mean |x(i) - x(i-1)| / 1.128. Neighbouring parts are close in time, so their difference contains only short-term noise, not the slow drift. The overall standard deviation would include the drift (test `test_moving_range_ignores_slow_drift`).

## 3. The Western Electric rules

| Rule | Fires when | Catches |
| --- | --- | --- |
| 1 | one point beyond 3 sigma | big sudden changes |
| 2 | 2 of 3 beyond 2 sigma, same side | medium shifts |
| 3 | 4 of 5 beyond 1 sigma, same side | small shifts (fired first here, Wed 09:08) |
| 4 | 8 in a row on one side | small sustained shifts |

The price: with all four rules, an in-control process raises a false alarm on about 1-2 % of points instead of 0.27 % (test `test_false_alarm_rates_in_control`). EWMA does the same job in one statistic: it averages recent points with weights 0.2, 0.16, 0.128, ..., so noise cancels and a sustained shift accumulates.

## 4. Choosing the test

| Situation | Test | Assumption to check |
| --- | --- | --- |
| two independent groups, means | Welch t (default), pooled t | approximate normality or large n; pooled also needs equal variances |
| same parts measured twice | paired t | normal differences |
| two groups, no normality | Mann-Whitney U | similar shapes |
| more than two groups | ANOVA, then Tukey HSD | normality, equal variances (Levene) |
| more than two groups, no normality | Kruskal-Wallis | |
| two categorical variables | chi-square | all expected counts >= 5, otherwise Fisher's exact test |
| two proportions | two-proportion z, Fisher for small counts | |
| linear relation | Pearson r, regression slope t test | linearity, constant residual spread |

Why Welch by default: if the variances are equal it loses almost nothing; if they are not, the pooled test gives wrong p-values. The F test for equal variances is itself very sensitive to non-normality, which is why Levene's test is used before ANOVA.

## 5. Reading p-values and intervals honestly

- p = 0.25 for the shift does **not** mean the shifts are equal. It means this data cannot show a difference. With 2 % failures, a test needs thousands of runs to detect a difference of one percentage point.
- An interval says more than a p-value: the Thu-Fri leak rise is +0.76 sccm with 95 % CI 0.65 to 0.87. It is both significant and large.
- Nine Shapiro-Wilk tests at 5 % produce about 0.45 false rejections by chance. Both rejections here come from single extreme values, so the report shows the test without them.
- Regression to the mean: parts retested *because* they read high will read lower the second time even if nothing changed. The retest drop here (0.67 sccm) is far bigger than that effect, so the re-seating itself changes the reading.

## 6. Capability and its uncertainty

Cpk = (USL - mean) / (3 sigma) for a one-sided limit. Cpk 1.33 means the nearer limit is 4 sigma away. From 57 parts, the leak test's Monday-Tuesday Cpk of 1.35 has a 95 % interval of 1.08 to 1.61: we cannot even be sure it meets 1.33. A Cpk known to +-0.10 needs about 384 parts. This is why automotive capability studies ask for at least 125 parts (25 subgroups of 5) and why a Cpk from 30 parts should always be given with its interval.

## 7. Likely questions

| Question | Answer |
| --- | --- |
| Why limits from Monday-Tuesday? | They are the only days the Tukey test shows as equal and before any failure; in a real plant, a period confirmed stable by its own chart. |
| Why individual values and not subgroups for LEAK-1? | One clutch unit is tested at a time, slowly; consecutive parts are the natural rational subgroup of 1. |
| Why is the change point not exactly Wednesday 06:00? | The generator steps once a day; a straight line fitted to steps starts rising a little before the first step. |
| Why does the p-chart need a different p-bar? | Monday-Tuesday had zero failures, so p-bar would be 0 and any single failure would be "out of control". |
| Isn't 4 rules = more false alarms? | Yes, about 1-2 % of points. The trade-off is the subject of ARL (average run length) tables. |
| Would you use this at work? | The I-MR chart with run rules on the leak tester, with the limits recomputed after each seal change, is a standard station monitor. |

## 8. Python and R

If the course labs use R, every test has a direct equivalent:

| Here | R |
| --- | --- |
| `welch_t`, `pooled_t`, `paired_t` | `t.test(x, y)`, `t.test(x, y, var.equal = TRUE)`, `t.test(x, y, paired = TRUE)` |
| `f_test`, `levene` | `var.test(x, y)`, `car::leveneTest(y ~ g)` |
| `mann_whitney`, `kruskal_wallis` | `wilcox.test(x, y)`, `kruskal.test(y ~ g)` |
| `anova_oneway`, Tukey | `aov(y ~ g)`, `TukeyHSD(aov(y ~ g))` |
| `chi2_independence`, Fisher | `chisq.test(tab, correct = FALSE)`, `fisher.test(tab)` |
| `ci_proportion` | `prop.test(k, n, correct = FALSE)$conf.int` (Wilson) |
| `linreg`, `pearson` | `lm(y ~ x)`, `cor.test(x, y)` |
| control charts | the `qcc` package |

## 9. Next steps

- [ ] Real data: export a week from a real tester (or from the Oracle database with `sql/export_measurements.sql`)
- [ ] Gauge R&R: how much of the leak variation is the tester itself
- [ ] ARL comparison of rule sets and EWMA lambda by simulation
- [ ] Recompute the limits automatically after a maintenance event
