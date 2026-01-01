"""report.md and the human-check sample for r5 (30 personas). No LLM calls; no wall-clock times in the outputs.

Usage: python scripts/v2r5_report.py
"""

import glob
import json
import os
import random
import re
from collections import Counter

D = "data_v2_preview_r5_30"
ATTRS = ["age", "household_children", "employment", "income", "education"]


def md(rows, head):
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def main():
    pids = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(D, "history", "*.json")))
    ld = lambda sub, p: json.load(open(os.path.join(D, sub, f"{p}.json")))
    P, H, M, G = ({p: ld(s, p) for p in pids} for s in ("personas", "history", "memory", "graph"))
    log = json.load(open(os.path.join(D, "generation_log.json")))
    pct = lambda a, b: f"{a}/{b} ({100 * a / b:.0f}%)" if b else "-"
    W = []
    w = W.append
    w("# Dataset v2, r5 — 30-persona trial of the r4 design with batch settings\n")
    w("Same design as r4 (fact graph + slot generation + code checks). Batch changes: assistant messages from code templates; memory chain and "
      "duplicate merging in code; model checks only on fixed random samples (session audit 10%, quote support 10% of rows, attribute labels 20% "
      "of entries). u001-u008 as before; u009-u030 new ProfileFoundry adults so that each age group has 5. Not committed; no attack run.\n")

    w("## 1. Personas [auto]\n")
    rows = []
    for p in pids:
        f = {k: v["value"] for k, v in P[p]["fields"].items()}
        rel = ", ".join(a["relation"] for a in f["co_resident_adults"]) + (f", {len(f['own_minor_children'])} minor child(ren) [synthetic]" if isinstance(f["own_minor_children"], list) and f["own_minor_children"] else "")
        rows.append([p, f["age"], f["age_group"], f["city"], rel or "alone", H[p]["status"], f"{len(H[p]['kept'])}/{H[p]['planned']}", len(H[p]["failed"]),
                     "ok" if H[p]["graph_ok"] else "FAILED", len(M[p]["raw"])])
    W += md(rows, ["persona", "age", "group", "city", "lives with", "status", "sessions", "failed sessions", "graph rules", "memory"])
    groups = Counter(P[p]["fields"]["age_group"]["value"] for p in pids)
    w(f"\nAge groups: {dict(sorted(groups.items()))}. Personas ok: {sum(H[p]['status'] == 'ok' for p in pids)}/{len(pids)}.\n")

    w("## 2. Generation and code checks [auto]\n")
    user_msgs = sum(1 for p in pids for s in H[p]["kept"] for t in s["turns"] if t["speaker"] == "User")
    first = sum(1 for p in pids for s in H[p]["kept"] for t in s["turns"] if t["speaker"] == "User" and t["attempts"] == 1)
    planned = sum(H[p]["planned"] for p in pids)
    kept = sum(len(H[p]["kept"]) for p in pids)
    reasons = Counter()
    for p in pids:
        for e in log.get(p, []):
            for a in (e.get("rejected") or e.get("attempts") or []):
                for pr in a["problems"]:
                    reasons[re.split(r":| \(", pr)[0]] += 1
    tmpl = sum(1 for p in pids for e in log.get(p, []) if e["kind"] == "template_rejected")
    W += md([["sessions planned", planned], ["sessions realised", pct(kept, planned)], ["user messages accepted at the first wording", pct(first, user_msgs)],
             ["assistant template messages rejected by the code checks", tmpl]], ["", "count"])
    w("\nRejection reasons over all rejected wordings: " + ", ".join(f"{k} {v}" for k, v in reasons.most_common()) + ".\n")
    w("Failed sessions (all kept as failed, none replaced):\n")
    W += [f"- {p} {f_['session_id']} ({f_['activity']}): “{f_['attempts'][-1]['text'][:130]}” — {'; '.join(f_['attempts'][-1]['problems'])[:160]}"
          for p in pids for f_ in H[p]["failed"]] or ["- none"]
    w("")

    w("## 3. Sampled model checks [auto]\n")
    au = [(p, s) for p in pids for s in H[p]["kept"] if "llm_audit_sampled" in s]
    fl = [(p, s, x) for p, s in au for x in s["llm_audit_sampled"]["problems"] if x["source"] != "code"]
    cl = Counter(c["kind"] for _, s in au for c in s["llm_audit_sampled"]["claims"])
    sup = Counter(it.get("quote_support_sampled") for p in pids for it in M[p]["raw"] if "quote_support_sampled" in it)
    labs = [(p, it) for p in pids for it in M[p]["raw"] if "annotation_sampled" in it]
    W += md([["sessions audited (10% sample)", len(au)], ["sessions with any audit flag", len(set((p, s["session_id"]) for p, s, _ in fl))],
             ["user statements in audited sessions: registered", pct(cl["registered"], sum(cl.values()))],
             ["memory rows checked for quote support (10% sample)", f"{sum(sup.values())}: " + ", ".join(f"{k} {v}" for k, v in sup.items())],
             ["memory entries with attribute labels (20% sample)", len(labs)]], ["", "result"])
    w("\nAudit flags (to be read by hand, section 6):\n")
    W += [f"- {p} {s['session_id']} {x['type']}: “{x['quote'][:90]}” — {str(x['reason'])[:120]}" for p, s, x in fl] or ["- none"]
    cs = Counter((f, it["annotation_sampled"]["status"][f]) for _, it in labs for f in ATTRS if it["annotation_sampled"]["text_label"][f] in ("direct", "indirect"))
    w("\nAttribute labels in the 20% sample (text label direct/indirect, by status):\n")
    cols = ["source_supported_cue", "unverified_link", "unsupported_association", "unknown_source"]
    W += md([[f] + [cs[(f, c)] for c in cols] for f in ATTRS], ["attribute"] + cols)
    w("")

    w("## 4. Memory [auto]\n")
    st = Counter()
    for p in pids:
        st.update(M[p]["stage_counts"])
    ent = [it for p in pids for it in M[p]["raw"]]
    links = Counter((a, it["generation_link"][a]) for it in ent for a in ("age", "household_children"))
    W += md([["rows returned by extraction", st["1_rows_returned_by_extraction"]], ["rows passing format checks", st["2_rows_passing_format_checks"]],
             ["merged as the same slots / same wording", f"{st['merged_same_slots']} / {st['merged_word_overlap']}"],
             ["final entries", st["3_entries_after_merging"]], ["entries tied to at least one slot", pct(sum(it["fact_basis"] == "registered" for it in ent), len(ent))],
             ["entries with more than one occurrence", sum(it["n_occurrences"] > 1 for it in ent)],
             ["entries linked to household (from graph nodes)", sum(links[("household_children", k)] for k in ("direct_source",))],
             ["entries linked to age through our child rule (co_generated)", links[("age", "co_generated")]],
             ["entries linked to age only through unverified ProfileFoundry links", links[("age", "unverified")]]], ["stage", "count"])
    w("")

    # human-check sample: 2 sessions and 5 memory entries per persona
    rng = random.Random("r5-human-sample")
    Q = ["# r5 human-check sample (2 sessions and 5 memory entries per persona, fixed seed)\n"]
    for p in pids:
        Q.append(f"\n## {p}\n")
        for s in rng.sample(H[p]["kept"], min(2, len(H[p]["kept"]))):
            Q.append(f"**{p} {s['session_id']} {s['activity']}** — slots: " + " | ".join(x["say"][:60] for x in s["slots"]))
            Q += [f"- {t['speaker']}: {t['text']}" for t in s["turns"]]
        for it in rng.sample(M[p]["raw"], min(5, len(M[p]["raw"]))):
            Q.append(f"- memory {it['memory_id']} ×{it['n_occurrences']} [{it['fact_basis']}; {', '.join(n for n in it['nodes'] if not n.startswith('session')) or '-'}]: "
                     f"“{it['text']}” ← “{it['quotes'][0]}”")
    open(os.path.join(D, "human_check_sample.md"), "w").write("\n".join(Q) + "\n")
    mr = os.path.join(D, "manual_review.md")
    w("## 5. Still unresolved\n")
    w("- Model checks are samples, so rates carry sampling error; nothing outside the samples was checked by a model.")
    w("- The code checks do not see meaning changes without new words.")
    w("- ProfileFoundry links between age and partner / adult children / parents / job / education / life events remain unverified.\n")
    if os.path.exists(mr):
        w(open(mr).read().rstrip())
    open(os.path.join(D, "report.md"), "w").write("\n".join(W) + "\n")
    print("\n".join(W))


if __name__ == "__main__":
    main()
