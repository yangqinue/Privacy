"""Re-run the dev_v3 violation judge (with the asks_event_time flag) on dev_v2 dialogues, so the flag is
comparable across all four modes. Writes runs/dev_v3/rejudge_v2/seed{S}/{pid}_{mode}.json; never touches dev_v2.

Usage: python rejudge_v3.py --servers http://localhost:11436=4,...
"""

import argparse
import concurrent.futures as cf
import glob
import json
import os

import run_dev3 as D3

HERE = os.path.dirname(os.path.abspath(__file__))


def rejudge(args, path, out_path):
    if os.path.exists(out_path):
        return
    c = json.load(open(path))
    js = []
    for t in c["turns"]:
        if t["role"] != "agent":
            continue
        j, _, _, used = D3.chat(args, [{"role": "user", "content": D3.VIOLATION_PROMPT.format(message=t["text"])}], 0.0,
                                D3.call_seed(c["seed"], c["persona_id"], "violation_v3", c["mode"], t["k"]))
        js.append({"k": t["k"], "label": j.get("label"), "quote": j.get("quote"), "is_probe": bool(j.get("is_probe")),
                   "asks_about_past": bool(j.get("asks_about_past")), "asks_event_time": bool(j.get("asks_event_time")),
                   "call_seed": used})
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump({"persona_id": c["persona_id"], "mode": c["mode"], "seed": c["seed"], "violation_judgements": js},
              open(out_path, "w"), indent=2, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2", default=os.path.join(HERE, "..", "runs", "dev_v2"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "runs", "dev_v3", "rejudge_v2"))
    ap.add_argument("--servers", default="http://localhost:11434=1")
    ap.add_argument("--model", default="qwen3:32b")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--num_ctx", type=int, default=16384)
    args = ap.parse_args()
    D3.POOL = D3.ServerPool(args.servers)
    jobs = []
    for f in sorted(glob.glob(os.path.join(args.v2, "seed*", "convs", "*.json"))):
        seed_dir = os.path.basename(os.path.dirname(os.path.dirname(f)))
        jobs.append((f, os.path.join(args.out, seed_dir, os.path.basename(f))))
    with cf.ThreadPoolExecutor(2 * D3.POOL.total_slots()) as ex:
        futs = {ex.submit(rejudge, args, a, b): a for a, b in jobs}
        for fut in cf.as_completed(futs):
            if fut.exception():
                print("FAILED", futs[fut], repr(fut.exception()), flush=True)
    print(f"rejudged {len(jobs)} dialogues", flush=True)


if __name__ == "__main__":
    main()
