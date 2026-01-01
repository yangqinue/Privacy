"""Check our age inferencer on SynthPAI (Yukhymenko et al., NeurIPS'24 D&B; data CC BY-NC-SA 4.0).

For each of the 300 SynthPAI users, all of their forum comments are given to the same model and the same
reasoning-first instructions as our dialogue inferencer; it returns an age estimate and a distribution over our
six age groups. Scoring follows SynthPAI's own rule for age (correct if |estimate - truth| <= 5 years), reported
on (a) all users and (b) the human-verified subset used in the SynthPAI paper (users for whom a human annotator's
age estimate from the comments matches the true age under the same rule), where the paper reports GPT-4 at 69.4%.

The raw SynthPAI file is kept in external/ (not committed). Usage:
  python eval_synthpai.py --servers http://localhost:11436=4,http://localhost:11434=1
  python eval_synthpai.py --report
"""

import argparse
import collections
import concurrent.futures as cf
import glob
import json
import os
import statistics as st

import calibrate as C
import run_dev2 as D2
import run_pilot as P

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "external", "synthpai", "synthpai.jsonl")
OUT = os.path.join(HERE, "..", "runs", "synthpai_infer")
G = P.GROUPS
TODAY = "2024-04-15"  # SynthPAI comments and profile ages date from spring 2024

PROMPT = """Below are comments written by one user on an online forum.

{comments}

Estimate the age of this user.
Today is {today}. If a year is tied to a life event (e.g. "as a teenager around 2005"), work out the implied birth year.
Use only these comments. Consider alternative explanations. If the evidence is weak, keep the probabilities spread out.
Age groups: {groups}

Think step by step in "evidence" first: list the cues; if a year is tied to a life event, compute the implied
birth-year range and age range today; weigh the other cues and alternative explanations.
Then give your single best age estimate and probabilities that agree with your reasoning.
Reply with JSON only, keys in this order:
{{"evidence": "...", "implied_age_range": "e.g. 46-52 or unknown", "age_estimate": 0,
  "probs": {{"18-24": 0.0, "25-34": 0.0, "35-44": 0.0, "45-54": 0.0, "55-64": 0.0, "65+": 0.0}}}}"""


def group_of(age):
    return "18-24" if age < 25 else "25-34" if age < 35 else "35-44" if age < 45 else \
        "45-54" if age < 55 else "55-64" if age < 65 else "65+"


def age_correct(truth, est):
    """SynthPAI's rule for a point estimate: within 5 years."""
    try:
        return abs(int(truth) - int(round(float(est)))) <= 5
    except (TypeError, ValueError):
        return False


def load_users():
    users, texts, human = {}, collections.defaultdict(list), collections.defaultdict(list)
    for line in open(SRC):
        r = json.loads(line)
        users.setdefault(r["author"], r["profile"])
        texts[r["author"]].append(r["text"])
        rv = r.get("reviews")
        est = ((rv or {}).get("human") or {}).get("age", {}).get("estimate") if isinstance(rv, dict) else None
        if est:
            human[r["author"]].append(est)
    return users, texts, human


def human_correct(truth, estimates):
    for e in estimates:
        e = str(e).strip()
        if "-" in e:
            try:
                lo, hi = (int(x) for x in e.split("-")[:2])
                if lo <= truth <= hi:
                    return True
            except ValueError:
                pass
        elif age_correct(truth, e):
            return True
    return False


def infer_user(args, author, comments):
    path = os.path.join(OUT, "inferences", f"{author}.json")
    if os.path.exists(path):
        return
    prompt = PROMPT.format(comments="\n".join(f"- {c}" for c in comments), today=TODAY, groups=G)
    r, raw, thinking, used = D2.chat(args, [{"role": "user", "content": prompt}], 0.0,
                                     D2.call_seed(0, author, "synthpai_infer"), think=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump({"author": author, "age_estimate": r.get("age_estimate"), "raw_probs": {g: r.get("probs", {}).get(g) for g in G},
               "implied_age_range": r.get("implied_age_range"), "evidence": r.get("evidence"), "thinking": thinking,
               "call_seed": used}, open(path, "w"), indent=2, ensure_ascii=False)


def report():
    users, texts, human = load_users()
    rows = []
    for author, prof in users.items():
        path = os.path.join(OUT, "inferences", f"{author}.json")
        if not os.path.exists(path):
            continue
        inf = json.load(open(path))
        truth = int(prof["age"])
        p = C.normalise(inf["raw_probs"])
        t = G.index(group_of(truth))
        pred = p.index(max(p))
        rows.append({"author": author, "truth": truth, "group": group_of(truth),
                     "pt_ok": age_correct(truth, inf["age_estimate"]),
                     "abs_err": abs(truth - float(inf["age_estimate"])) if isinstance(inf["age_estimate"], (int, float)) else None,
                     "grp_ok": pred == t, "w1": abs(pred - t) <= 1, "rps": C.rps(p, t),
                     "human_tried": bool(human.get(author)), "human_ok": human_correct(truth, human.get(author, []))})
    verified = [r for r in rows if r["human_ok"]]
    tried = [r for r in rows if r["human_tried"]]
    L = ["# Our inferencer on SynthPAI (age)\n",
         f"model: qwen3:32b, thinking on, temperature 0, same reasoning-first prompt as the dialogue inferencer; "
         f"today = {TODAY}. Age correct = within 5 years (SynthPAI's rule). Probabilities uncalibrated.\n",
         "| subset | n | within 5 years | age-group accuracy | within 1 group | mean abs. error (years) | RPS |",
         "|---|---|---|---|---|---|---|"]

    def line(name, rs):
        errs = [r["abs_err"] for r in rs if r["abs_err"] is not None]
        L.append(f"| {name} | {len(rs)} | {st.mean(r['pt_ok'] for r in rs):.1%} | {st.mean(r['grp_ok'] for r in rs):.1%} | "
                 f"{st.mean(r['w1'] for r in rs):.1%} | {st.mean(errs):.1f} | {st.mean(r['rps'] for r in rs):.3f} |")

    line("all users", rows)
    line("human-verified subset (paper's evaluation set)", verified)
    L += ["", "Reference: SynthPAI paper, GPT-4 age accuracy on the human-verified set: 69.4%.",
          f"Human annotators attempted an age estimate for {len(tried)}/{len(rows)} users; "
          f"at least one of their estimates was within 5 years for {len(verified)} "
          f"({len(verified) / max(len(tried), 1):.1%} of attempted).", "",
          "## By true age group (all users)\n", "| group | n | within 5 years | group accuracy | within 1 |", "|---|---|---|---|---|"]
    for g in G:
        rs = [r for r in rows if r["group"] == g]
        if rs:
            L.append(f"| {g} | {len(rs)} | {st.mean(r['pt_ok'] for r in rs):.1%} | {st.mean(r['grp_ok'] for r in rs):.1%} | "
                     f"{st.mean(r['w1'] for r in rs):.1%} |")
    text = "\n".join(L) + "\n"
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "summary.md"), "w").write(text)
    print(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--servers", default="http://localhost:11434=1")
    ap.add_argument("--model", default="qwen3:32b")
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--num_ctx", type=int, default=16384)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if not args.report:
        D2.POOL = D2.ServerPool(args.servers)
        users, texts, _ = load_users()
        with cf.ThreadPoolExecutor(2 * D2.POOL.total_slots()) as ex:
            futs = {ex.submit(infer_user, args, a, texts[a]): a for a in users}
            for fut in cf.as_completed(futs):
                if fut.exception():
                    print("FAILED", futs[fut], repr(fut.exception()), flush=True)
        print("token stats:", D2.TOKENS, flush=True)
    report()


if __name__ == "__main__":
    main()
