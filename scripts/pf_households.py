"""Generate US households with ProfileFoundry at a fixed reference date (the CLI uses date.today()).

ProfileFoundry (Selvam & Ghosh, arXiv 2606.26403; code under the ProfileFoundry Citation License 1.0) is run from
external/ProfileFoundry_src (GitHub commit recorded in the output manifest) with its extra dependencies in
external/pf_libs.

Usage:
  PYTHONPATH=external/ProfileFoundry_src/src:external/pf_libs \
    python scripts/pf_households.py --n 1500 --seed 0 --out data_v2_preview/pf/us_households.jsonl
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess

from profilefoundry.linkage.orchestrator import iter_households

REFERENCE = dt.date(2026, 10, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True, help="number of households")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--locale", default="US")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    n = 0
    with open(args.out, "w", encoding="utf-8") as f:
        for bundle in iter_households(args.locale, args.n, args.seed, today=REFERENCE):
            for p in bundle.persons:
                f.write(p.model_dump_json() + "\n")
                n += 1
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "external", "ProfileFoundry_src")
    commit = subprocess.run(["git", "-C", src, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    sha = hashlib.sha256(open(args.out, "rb").read()).hexdigest()
    json.dump({"generator": "ProfileFoundry", "commit": commit, "locale": args.locale, "households": args.n,
               "persons": n, "seed": args.seed, "reference_date": REFERENCE.isoformat(), "sha256": sha},
              open(args.out + ".manifest.json", "w"), indent=2)
    print(f"wrote {n} persons in {args.n} households; sha256 {sha[:12]}")


if __name__ == "__main__":
    main()
