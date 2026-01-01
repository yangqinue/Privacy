"""Analyse dev_v3 together with dev_v2: benign / fixed / adaptive (dev_v2) + adaptive_seeded (dev_v3).

Same pre-specified metrics as analyze_dev2.py (primary: calibrated RPS of the true age group), the frozen dev_v2
calibration, the same seeds and the same shared openings. Main question: does seeding the adaptive attacker with
the fixed question bank beat the fixed list (adaptive_seeded - fixed)?
Event-time policy B: dialogues where the agent asked when a past event happened are reported separately.
"""

import argparse
import json
import os
import statistics as st

import analyze_dev as A
import analyze_dev2 as AD2
import run_pilot as P

HERE = os.path.dirname(os.path.abspath(__file__))
G = P.GROUPS
MODES = ["benign", "fixed", "adaptive", "adaptive_seeded"]
COMPARISONS = [("adaptive_seeded", "fixed"), ("adaptive_seeded", "adaptive"), ("adaptive_seeded", "benign"),
               ("fixed", "benign"), ("adaptive", "benign")]


def attach_v3_judgements(rows, v3, rejudge_dir):
    """Replace judge-derived fields with the v3 judge (same prompt for every mode)."""
    for r in rows:
        if r["mode"] == "adaptive_seeded":
            path = os.path.join(v3, f"seed{r['seed']}", "convs", f"{r['pid']}_{r['mode']}.json")
        else:
            path = os.path.join(rejudge_dir, f"seed{r['seed']}", f"{r['pid']}_{r['mode']}.json")
        if not os.path.exists(path):
            r["event_time"] = None
            continue
        js = {j["k"]: j for j in json.load(open(path))["violation_judgements"]}
        r["event_time"] = any(j.get("asks_event_time") for j in js.values())
        r["explicit"] = any(j["label"] == "explicit" for j in js.values())
        r["ambiguous"] = any(j["label"] == "ambiguous" for j in js.values())
        r["n_probe"] = sum(j["is_probe"] for j in js.values())
        r["asks_past"] = sum(j["asks_about_past"] for j in js.values())
        if r["leak_k"]:
            prev = js.get(r["leak_k"] - 1)
            r["elicited"] = bool(prev and (prev["asks_about_past"] or prev.get("asks_event_time")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2", default=os.path.join(HERE, "..", "runs", "dev_v2"))
    ap.add_argument("--v3", default=os.path.join(HERE, "..", "runs", "dev_v3"))
    args = ap.parse_args()
    AD2.CAL.update(json.load(open(os.path.join(args.v2, "calibration.json"))))
    seeds2, rows2, refs, _ = A.load(args.v2)
    seeds3, rows3, _, _ = A.load(args.v3)
    seeds = sorted(set(seeds2) & set(seeds3))
    rows = [r for r in rows2 + rows3 if r["seed"] in seeds]
    attach_v3_judgements(rows, args.v3, os.path.join(args.v3, "rejudge_v2"))
    group_of = {r["pid"]: r["group"] for r in rows}
    m_of, ci = AD2.m_of, AD2.ci
    L = []
    w = L.append

    w("# dev_v3 results (adaptive_seeded, compared with dev_v2 modes)\n")
    w(f"seeds: {seeds}; people: {len(group_of)}; conversations: {len(rows)}; calibration from dev_v2: "
      f"T={AD2.CAL['T']}, delta={AD2.CAL['delta']}")
    missing = sum(r["event_time"] is None for r in rows)
    w(f"v3 judge available for {len(rows) - missing}/{len(rows)} conversations (rest: original dev_v2 judge)\n")

    w("## Mode means (final turn)\n")
    w("| mode | RPS | expected distance | accuracy | within 1 | strong cue leaked | asked about the past (msgs/conv) | asked when an event happened (convs) | mean length |")
    w("|---|---|---|---|---|---|---|---|---|")
    for mode in MODES:
        rs = [r for r in rows if r["mode"] == mode]
        if not rs:
            continue
        ms = [m_of(r) for r in rs]
        et = [r for r in rs if r["event_time"]]
        w(f"| {mode} | {st.mean(m['rps'] for m in ms):.3f} | {st.mean(m['dist'] for m in ms):.2f} | "
          f"{st.mean(m['acc'] for m in ms):.2f} | {st.mean(m['w1'] for m in ms):.2f} | "
          f"{sum(bool(r['leak_k']) for r in rs)}/{len(rs)} | {st.mean(r.get('asks_past', 0) for r in rs):.1f} | "
          f"{len(et)}/{len(rs)} | {st.mean(r['n_a'] for r in rs):.1f} |")
    w("")

    w("## Paired comparisons (negative = A leaks more)\n")
    w("| comparison | Δ RPS (primary) | Δ expected distance | Δ accuracy | Δ within-1 | RPS win / tie / loss for A |")
    w("|---|---|---|---|---|---|")
    for a, b in COMPARISONS:
        cells = [ci(A.paired(rows, a, b, lambda r, k=k: m_of(r)[k]), group_of) for k in ("rps", "dist", "acc", "w1")]
        dr = A.paired(rows, a, b, lambda r: m_of(r)["rps"])
        win, loss = sum(v < -0.005 for v in dr.values()), sum(v > 0.005 for v in dr.values())
        w(f"| {a} - {b} | " + " | ".join(cells) + f" | {win} / {len(dr) - win - loss} / {loss} |")
    w("")

    w("## Per seed (Δ RPS)\n")
    w("| comparison | " + " | ".join(f"seed {s}" for s in seeds) + " |")
    w("|---|" + "---|" * len(seeds))
    for a, b in COMPARISONS:
        w(f"| {a} - {b} | " + " | ".join(ci(A.paired(rows, a, b, lambda r: m_of(r)["rps"], seed=s), group_of)
                                         for s in seeds) + " |")
    w("")

    w("## Event-time questions (policy B)\n")
    seeded = [r for r in rows if r["mode"] == "adaptive_seeded"]
    for label, sub in (("asked when an event happened", [r for r in seeded if r["event_time"]]),
                       ("did not ask", [r for r in seeded if not r["event_time"]])):
        if sub:
            w(f"- adaptive_seeded, {label}: n={len(sub)}, final RPS {st.mean(m_of(r)['rps'] for r in sub):.3f}, "
              f"strong cue leaked {sum(bool(r['leak_k']) for r in sub)}/{len(sub)}")
    keep = [r for r in rows if not (r["mode"] == "adaptive_seeded" and r["event_time"])]
    w(f"\nadaptive_seeded - fixed, excluding seeded dialogues with event-time questions (descriptive): "
      f"{ci(A.paired(keep, 'adaptive_seeded', 'fixed', lambda r: m_of(r)['rps']), group_of)}\n")

    w("## Agent behaviour (v3 judge)\n")
    w("| mode | explicit age request | ambiguous | probing msgs/conv | booking ok |")
    w("|---|---|---|---|---|")
    for mode in MODES:
        rs = [r for r in rows if r["mode"] == mode]
        if rs:
            w(f"| {mode} | {sum(r['explicit'] for r in rs)}/{len(rs)} | {sum(r['ambiguous'] for r in rs)}/{len(rs)} | "
              f"{st.mean(r['n_probe'] for r in rs):.1f} | {sum(r['booking'] == 'ok' for r in rs)}/{len(rs)} |")

    open(os.path.join(args.v3, "summary.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
