"""Browse saved dialogues.

List (one line per dialogue, filterable):
  python show_dialogue.py --list --version dev_v3 --mode adaptive_seeded --leaked
  python show_dialogue.py --list --version dev_v2 --pid p091      (or: --list p091)
Show one dialogue in full (assistant / agent turns, agent private notes, judge flags, inference after each turn):
  python show_dialogue.py p029 --seed 2 --mode adaptive_seeded --version dev_v3
  python show_dialogue.py p029 --seed 2 --mode adaptive_seeded --thinking   # also print the inferencer's reasoning

Versions: dev_v1 (modes benign/fixed/adaptive, seed 0, uncalibrated), dev_v2 (benign/fixed/adaptive, seeds 0-2),
dev_v3 (adaptive_seeded, seeds 0-2). Calibrated probabilities use runs/dev_v2/calibration.json.
"""

import argparse
import glob
import json
import os
import re

import calibrate as C
import run_pilot as P

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "runs")
G = P.GROUPS
CAL = json.load(open(os.path.join(RUNS, "dev_v2", "calibration.json")))


def cal(raw):
    return C.calibrate(raw, CAL["T"], CAL["delta"])


def persona(pid):
    p = json.load(open(os.path.join(P.DATA, "personas", f"{pid}.json")))
    m = json.load(open(os.path.join(P.DATA, "memories", f"{pid}.json")))
    return p, m


def judgements(version, c):
    """v3 judge where available (dev_v3 dialogues, or dev_v2 re-judged), else the original judge."""
    js = c.get("violation_judgements", [])
    rj = os.path.join(RUNS, "dev_v3", "rejudge_v2", f"seed{c['seed']}", f"{c['persona_id']}_{c['mode']}.json")
    if version == "dev_v2" and os.path.exists(rj):
        js = json.load(open(rj))["violation_judgements"]
    return {j["k"]: j for j in js}


def summary(version, path):
    c = json.load(open(path))
    p, m = persona(c["persona_id"])
    true = p["ground_truth"]["age_group"]
    t = G.index(true)
    year = re.search(r"\b(\d{4})\b", p["strong_cue"]["text"]).group(1)
    leak_k = next((x["k"] for x in c["turns"] if x["role"] == "assistant" and year in x["text"]), None)
    r_open = C.rps(cal(c["inference"][0]["raw_probs"]), t)
    r_end = C.rps(cal(c["inference"][-1]["raw_probs"]), t)
    return {"pid": c["persona_id"], "seed": c["seed"], "mode": c["mode"], "true": true, "age": p["ground_truth"]["age"],
            "turns": c["n_assistant_messages"], "leak_k": leak_k, "rps_open": r_open, "rps_end": r_end,
            "booked": bool(c.get("booking")), "path": os.path.relpath(path, os.path.join(HERE, ".."))}


def list_dialogues(args):
    pat = os.path.join(RUNS, args.version, f"seed{args.seed if args.seed is not None else '*'}", "convs",
                       f"{args.pid or '*'}_{args.mode or '*'}.json")
    rows = [summary(args.version, f) for f in sorted(glob.glob(pat))]
    if args.mode:  # glob '*_fixed' would not match 'adaptive_seeded' wrongly, but filter exactly anyway
        rows = [r for r in rows if r["mode"] == args.mode]
    if args.leaked:
        rows = [r for r in rows if r["leak_k"]]
    rows.sort(key=lambda r: r["rps_end"] - r["rps_open"])
    print(f"{'pid':5} {'seed':>4} {'mode':16} {'true':6} {'age':>3} {'turns':>5} {'strong cue':>10} "
          f"{'RPS open->end':>15}  file")
    for r in rows:
        print(f"{r['pid']:5} {r['seed']:>4} {r['mode']:16} {r['true']:6} {r['age']:>3} {r['turns']:>5} "
              f"{('turn ' + str(r['leak_k'])) if r['leak_k'] else '-':>10} {r['rps_open']:.3f}->{r['rps_end']:.3f}  {r['path']}")
    print(f"\n{len(rows)} dialogues (sorted by RPS change; most negative = most leakage first)")


def show(args):
    seed = 0 if args.seed is None else args.seed
    path = os.path.join(RUNS, args.version, f"seed{seed}", "convs", f"{args.pid}_{args.mode}.json")
    c = json.load(open(path))
    p, m = persona(args.pid)
    true = p["ground_truth"]["age_group"]
    t = G.index(true)
    print(f"== {args.version} / seed {seed} / {args.pid} / {args.mode}   ({os.path.relpath(path, os.path.join(HERE, '..'))})")
    print(f"TRUE (hidden from all agents): age {p['ground_truth']['age']} ({true}); {p['profile']['household']}; "
          f"{p['profile']['work_pattern']}; {p['profile']['occupation']}")
    print(f"strong cue in memory: {p['strong_cue']['text']}")
    print("memory items relevant to concerts:")
    for it in m["memory"]:
        if P.ACTIVITY in it["relevant_activities"]:
            print(f"   - [{it['cue_type']}] {it['text']}")
    inf = {i["k"]: i for i in c["inference"]}
    jud = judgements(args.version, c)
    for x in c["turns"]:
        if x["role"] == "assistant":
            i = inf.get(x["k"])
            print(f"\n[ASSISTANT {x['k']}] {x['text']}")
            if i:
                pc = cal(i["raw_probs"])
                top = G[pc.index(max(pc))]
                print(f"   >> inferencer: implied age {i.get('implied_age_range')}; most likely {top}; "
                      f"P(true {true}) = {pc[t]:.2f} (calibrated); RPS = {C.rps(pc, t):.3f}")
                if args.thinking and i.get("thinking"):
                    print("   >> reasoning: " + i["thinking"].replace("\n", " ")[:2000])
        else:
            j = jud.get(x["k"], {})
            print(f"\n[AGENT {x['k']}] {x['text']}")
            if x.get("private_notes"):
                print(f"   (private notes: {x['private_notes']})")
            flags = [f"label={j.get('label')}"] + [k for k in ("is_probe", "asks_about_past", "asks_event_time") if j.get(k)]
            if x.get("confirmation_ignored"):
                flags.append("confirmation_ignored")
            print(f"   (judge: {', '.join(flags)})")
    print(f"\nBOOKING: {c.get('booking')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pid", nargs="?")
    ap.add_argument("--pid", dest="pid_opt", help="same as the positional persona id")
    ap.add_argument("--version", default="dev_v3", choices=["dev_v1", "dev_v2", "dev_v3"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--mode", help="benign | fixed | adaptive | adaptive_seeded")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--leaked", action="store_true", help="only dialogues where the year-anchored memory was stated")
    ap.add_argument("--thinking", action="store_true", help="print the inferencer's reasoning too")
    args = ap.parse_args()
    args.pid = args.pid or args.pid_opt
    if args.list or not args.pid:
        list_dialogues(args)
    else:
        if not args.mode:
            raise SystemExit("--mode is required to show one dialogue")
        show(args)


if __name__ == "__main__":
    main()
