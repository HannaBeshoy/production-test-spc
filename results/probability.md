# Probability questions on the test week

## 1. Is Friday's clutch result bad luck? (binomial and Poisson)

Monday to Thursday, 3 of 353 first-attempt clutch-unit runs failed: p = 0.0085.
On Friday 8 of 90 failed. If nothing had changed, the number of failures X in 90 runs
would be Binomial(90, 0.0085) with E[X] = 0.76 and Var[X] = 0.76.

- P(X >= 8) = 1.14e-06 (binomial)
- P(X >= 8) = 1.48e-06 (Poisson with lambda = n p = 0.765)

Both say the same: about one Friday in a million would look like this by chance, so something changed.
The Poisson value is close to the binomial one because n is large and p is small.

## 2. How much can a FAIL be trusted? (Bayes' theorem)

Assumed numbers, to show the effect: 1 % of parts are really bad and the tester catches 99 % of them.

| Tester | P(FAIL given good part) | P(part is bad given FAIL) |
| --- | --- | --- |
| healthy | 0.5% | 66.7% |
| worn seal | 5.0% | 16.7% |

With a healthy tester two of three rejected parts are really bad. With a worn seal only one in six is:
most rejects are good parts, so a FAIL from a worn tester says little about the part.

## 3. First-pass yield of the whole line (independent events)

A part must pass every station. If the stations fail independently, the pass probabilities multiply:

- EOL-1: 9 of 346 failed
- EOL-2: 2 of 99 failed
- LEAK-1: 8 of 145 failed
- TORQ-2: 2 of 100 failed
- VIS-1: 3 of 349 failed

P(no station fails) = 0.876, so about 12.4% of parts would fail somewhere if each part visited all five stations.
