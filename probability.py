"""Probability questions on the production-test week (course lectures 1-6).

    python probability.py        # prints the answers and writes results/probability.md
"""
from __future__ import annotations

import csv
from pathlib import Path

from spc import probability as pr

ROOT = Path(__file__).resolve().parent


def main() -> str:
    runs = [r for r in csv.DictReader(open(ROOT / "data" / "runs.csv"))
            if r["attempt"] == "1" and r["result"] != "ABORT"]
    cru = [r for r in runs if r["product"] == "CRU-200"]
    base = [r for r in cru if r["day"] != "Fri"]
    fri = [r for r in cru if r["day"] == "Fri"]
    k0, n0 = sum(r["result"] == "FAIL" for r in base), len(base)
    k1, n1 = sum(r["result"] == "FAIL" for r in fri), len(fri)
    p0 = k0 / n0
    mean, var = pr.binom_mean_var(n1, p0)
    lam = n1 * p0
    stations = {}
    for r in runs:
        s = stations.setdefault(r["station"], [0, 0])
        s[0] += r["result"] == "FAIL"
        s[1] += 1
    yield_all = pr.first_pass_all_good([f / n for f, n in stations.values()])

    out = ["# Probability questions on the test week", "",
           "## 1. Is Friday's clutch result bad luck? (binomial and Poisson)", "",
           f"Monday to Thursday, {k0} of {n0} first-attempt clutch-unit runs failed: p = {p0:.4f}.",
           f"On Friday {k1} of {n1} failed. If nothing had changed, the number of failures X in {n1} runs",
           f"would be Binomial({n1}, {p0:.4f}) with E[X] = {mean:.2f} and Var[X] = {var:.2f}.", "",
           f"- P(X >= {k1}) = {pr.binom_sf(k1, n1, p0):.2e} (binomial)",
           f"- P(X >= {k1}) = {pr.poisson_sf(k1, lam):.2e} (Poisson with lambda = n p = {lam:.3f})", "",
           "Both say the same: about one Friday in a million would look like this by chance, so something changed.",
           "The Poisson value is close to the binomial one because n is large and p is small.", "",
           "## 2. How much can a FAIL be trusted? (Bayes' theorem)", "",
           "Assumed numbers, to show the effect: 1 % of parts are really bad and the tester catches 99 % of them.", "",
           "| Tester | P(FAIL given good part) | P(part is bad given FAIL) |", "| --- | --- | --- |"]
    for label, fa in (("healthy", 0.005), ("worn seal", 0.05)):
        out.append(f"| {label} | {fa:.1%} | {pr.bayes_posterior(0.01, 0.99, fa):.1%} |")
    out += ["",
            "With a healthy tester two of three rejected parts are really bad. With a worn seal only one in six is:",
            "most rejects are good parts, so a FAIL from a worn tester says little about the part.", "",
            "## 3. First-pass yield of the whole line (independent events)", "",
            "A part must pass every station. If the stations fail independently, the pass probabilities multiply:", ""]
    out += [f"- {name}: {f} of {n} failed" for name, (f, n) in sorted(stations.items())]
    out += ["", f"P(no station fails) = {yield_all:.3f}, so about {1 - yield_all:.1%} of parts would fail somewhere "
                "if each part visited all five stations."]
    text = "\n".join(out) + "\n"
    (ROOT / "results" / "probability.md").write_text(text)
    return text


if __name__ == "__main__":
    print(main())
