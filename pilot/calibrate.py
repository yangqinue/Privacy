"""Fit the inferencer's temperature on shadow data only (attacker-side calibration).

p_cal = softmax(log(p_raw_normalised + delta) / T), with (T, delta) chosen on a grid to minimise mean log loss
over every inference point (all turns, all modes) of the shadow calibration runs. The fitted values are frozen in
calibration.json and then applied unchanged to dev / test; dev data is never used here.

Usage: python calibrate.py --shadow ../runs/dev_v2/shadow --out ../runs/dev_v2/calibration.json
"""

import argparse
import glob
import json
import math
import os

import run_pilot as P

GROUPS = P.GROUPS


def normalise(raw):
    v = []
    for g in GROUPS:
        try:
            v.append(max(float(raw.get(g) or 0), 0.0))
        except (TypeError, ValueError):
            v.append(0.0)
    s = sum(v)
    return [x / s for x in v] if s > 0 else [1 / 6] * 6


def calibrate(raw, T, delta):
    logits = [math.log(x + delta) / T for x in normalise(raw)]
    m = max(logits)
    e = [math.exp(l - m) for l in logits]
    s = sum(e)
    return [x / s for x in e]


def rps(p, t):
    cp, s = 0.0, 0.0
    for i in range(len(GROUPS) - 1):
        cp += p[i]
        s += (cp - (1.0 if i >= t else 0.0)) ** 2
    return s / (len(GROUPS) - 1)


def ece(points, fn, bins=10):
    """Top-label expected calibration error."""
    tot, acc = [0] * bins, [[0, 0.0, 0.0] for _ in range(bins)]
    for raw, t in points:
        p = fn(raw)
        c = max(p)
        b = min(int(c * bins), bins - 1)
        acc[b][0] += 1
        acc[b][1] += c
        acc[b][2] += float(p.index(c) == t)
    n = len(points)
    return sum(abs(a[1] - a[2]) for a in acc if a[0]) / n


def load_points(shadow_dir):
    pts = []
    for f in glob.glob(os.path.join(shadow_dir, "seed*", "convs", "*.json")):
        c = json.load(open(f))
        true = json.load(open(os.path.join(P.DATA, "personas", f"{c['persona_id']}.json")))["ground_truth"]["age_group"]
        for inf in c["inference"]:
            pts.append((inf["raw_probs"], GROUPS.index(true)))
    return pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shadow", default=os.path.join(os.path.dirname(__file__), "..", "runs", "dev_v2", "shadow"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "runs", "dev_v2", "calibration.json"))
    args = ap.parse_args()
    pts = load_points(args.shadow)
    if not pts:
        raise SystemExit("no shadow inference points found")

    def nll(T, d):
        return sum(-math.log(calibrate(r, T, d)[t]) for r, t in pts) / len(pts)

    grid_T = [round(0.25 * 1.1 ** i, 4) for i in range(45)]  # 0.25 .. ~16
    grid_d = [0.001, 0.003, 0.01, 0.03, 0.1]
    best = min(((nll(T, d), T, d) for T in grid_T for d in grid_d))
    _, T, d = best
    before = lambda r: [(1 - 0.01) * x + 0.01 / 6 for x in normalise(r)]
    after = lambda r: calibrate(r, T, d)
    report = {
        "method": "p_cal = softmax(log(p + delta) / T), grid search minimising mean log loss on shadow data",
        "T": T, "delta": d, "n_points": len(pts),
        "n_conversations": len(glob.glob(os.path.join(args.shadow, "seed*", "convs", "*.json"))),
        "fit_metrics": {
            "log_loss_before(eps=0.01)": sum(-math.log(before(r)[t]) for r, t in pts) / len(pts),
            "log_loss_after": best[0],
            "rps_before": sum(rps(normalise(r), t) for r, t in pts) / len(pts),
            "rps_after": sum(rps(after(r), t) for r, t in pts) / len(pts),
            "ece_before": ece(pts, before), "ece_after": ece(pts, after),
        },
    }
    json.dump(report, open(args.out, "w"), indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
