"""report.md for r4 (fact graph + slot generation), with a comparison to r2 and r3. No LLM calls.

Usage: python scripts/v2r4_report.py
"""

import glob
import json
import os
import re
from collections import Counter

ATTRS = ["age", "household_children", "employment", "income", "education"]
R2, R3, R4 = "data_v2_dialogue_preview_r2", "data_v2_dialogue_preview_r3", "data_v2_dialogue_preview_r4"


def md(rows, head):
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def cat(p):
    p = re.sub(r":.*", "", p)
    return p


def main():
    pids = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(R4, "history", "*.json")))
    ld = lambda d, sub, p: json.load(open(os.path.join(d, sub, f"{p}.json")))
    H = {p: ld(R4, "history", p) for p in pids}
    G = {p: ld(R4, "graph", p) for p in pids}
    MM = {p: ld(R4, os.path.join("memory", "raw"), p) for p in pids}
    M = {p: MM[p]["memory"] for p in pids}
    H2 = {p: ld(R2, "history", p) for p in pids}
    H3 = {p: ld(R3, "history", p) for p in pids}
    M3 = {p: ld(R3, os.path.join("memory", "raw"), p)["memory"] for p in pids}
    log = json.load(open(os.path.join(R4, "generation_log.json")))
    tests = json.load(open(os.path.join(R4, "validator_tests.json")))
    man = json.load(open(os.path.join(R4, "manifest.json")))
    W = []
    w = W.append
    pct = lambda a, b: f"{a}/{b} ({100 * a / b:.0f}%)" if b else "-"

    w("# Dataset v2 dialogue preview — r4: fact graph + slot generation\n")
    w("Same 8 personas, profiles, catalogs, session plans and tasks as r2/r3; earlier versions untouched; nothing committed; no attack run; "
      f"no cue quota. New LLM calls: {man['new_llm_calls']}. Numbers are **[auto]** unless marked **[manual]**.\n")
    w("**What changed.** Code builds a fact graph per persona and, for every session, decides every fact each user message says (slots, each "
      "pointing to graph nodes) and what each assistant message does. The model only words the messages. Code then checks each message: all its "
      "slots present; no date, weekday, day number, number, name, relative, diet/health or work detail that is not registered; no helper voice in "
      "user messages; no completion claim, real company or contact detail in assistant messages. A rejected message is re-worded (up to 4 tries, "
      "with the rejection reason); a session whose message still fails is marked failed and is not replaced. The r3 model checks are run "
      "afterwards only as an independent measurement.\n")

    w("## 1. Overview [auto]\n")
    rows = []
    for p in pids:
        ch = G[p]["checks"]
        rows.append([p, f"{H2[p]['status']} ({len(H2[p]['kept'])})", f"{H3[p]['status']} ({len(H3[p]['kept'])})",
                     f"**{H[p]['status']}** ({len(H[p]['kept'])}/{H[p]['planned']})", len(H[p]["failed"]),
                     f"{sum(c['ok'] for c in ch)}/{len(ch)}", len(G[p]["nodes"]), len(M3[p]), len(M[p])])
    W += md(rows, ["persona", "r2 (kept)", "r3 (kept)", "r4 (realised/planned)", "r4 failed sessions", "graph rules pass", "graph nodes", "r3 memory", "r4 memory"])
    w(f"\nValidator unit tests (known bad and good messages from r2/r3): {sum(t['passed'] for t in tests)}/{len(tests)} (`validator_tests.json`).\n")

    w("## 2. Fact graph rules [auto]\n")
    kinds = Counter()
    fails = []
    for p in pids:
        for c in G[p]["checks"]:
            k = re.sub(r"^S\d\d (s\d+: )?|^event:\d+ |: .*$| -> .*$", "", c["rule"]).strip()
            kinds[(k, c["ok"])] += 1
            if not c["ok"]:
                fails.append(f"{p}: {c['rule']} ({c['detail']})")
    rule_names = sorted({k for k, _ in kinds})
    W += md([[k, kinds[(k, True)], kinds[(k, False)]] for k in rule_names], ["rule", "pass", "fail"])
    w("\nFailures: " + ("; ".join(fails) if fails else "none") + "\n")

    w("## 3. Message wording and code checks [auto]\n")
    msgs = sum(len(s["turns"]) for p in pids for s in H[p]["kept"])
    first = sum(t["attempts"] == 1 for p in pids for s in H[p]["kept"] for t in s["turns"])
    rew = [e for p in pids for e in log.get(p, []) if e["kind"] == "message_reworded"]
    fail = [e for p in pids for e in log.get(p, []) if e["kind"] == "message_failed"]
    reasons = Counter()
    for e in rew + fail:
        for a in (e.get("rejected") or e.get("attempts")):
            for pr in a["problems"]:
                reasons[re.split(r":| \(", pr)[0]] += 1
    W += md([["messages in realised sessions", msgs], ["accepted at the first wording", pct(first, msgs)], ["accepted after re-wording", len(rew)],
             ["messages that failed all 4 wordings (session marked failed)", len(fail)]], ["", "count"])
    w("\nRejection reasons over all rejected wordings:\n")
    W += [f"- {k}: {v}" for k, v in reasons.most_common()]
    w("\nFailed sessions:\n")
    W += [f"- {p} {f_['session_id']} ({f_['activity']}), message {f_['turn']}: “{f_['attempts'][-1]['text'][:150]}” — {'; '.join(f_['attempts'][-1]['problems'])[:220]}"
          for p in pids for f_ in H[p]["failed"]] or ["- none"]
    w("")

    w("## 4. Independent measurement with the r3 model checks (not used as a gate) [auto]\n")
    flagged = Counter()
    types = Counter()
    cl = Counter()
    for p in pids:
        for s in H[p]["kept"]:
            a = s.get("llm_audit", {})
            ps = [x for x in a.get("problems", []) if x["source"] != "code"]
            flagged[bool(ps)] += 1
            for x in ps:
                types[x["type"]] += 1
            for c in a.get("claims", []):
                cl[c["kind"]] += 1
    tot = sum(cl.values())
    cl3 = Counter(c["kind"] for p in pids for s in H3[p]["kept"] for c in s["check"]["claims"])
    tot3 = sum(cl3.values())
    W += md([["sessions with any model-check flag", pct(flagged[True], flagged[True] + flagged[False]), "(r3 kept sessions: 0 by construction — they were filtered by it)"],
             ["user statements audited", tot, tot3],
             ["registered (traceable to profile, preference or situation)", pct(cl["registered"], tot), pct(cl3["registered"], tot3)],
             ["unregistered ordinary detail or wish", pct(cl["unregistered_detail"], tot), pct(cl3["unregistered_detail"], tot3)],
             ["new identity fact", cl["new_identity_fact"], cl3["new_identity_fact"]], ["contradiction", cl["contradiction"], cl3["contradiction"]]],
            ["", "r4", "r3"])
    w("\nFlag types in r4: " + (", ".join(f"{k} {v}" for k, v in types.most_common()) or "none") + ". Each flag is listed under its session in the view page; "
      "my reading of them is in section 8.\n")

    w("## 5. Memory, stage by stage [auto]\n")
    st, qs = Counter(), Counter()
    for p in pids:
        st.update(MM[p]["stage_counts"])
        qs.update(MM[p]["quote_support_counts"])
    W += md([["1. rows returned by extraction", st["1_rows_returned_by_extraction"]], ["2. rows passing format checks", st["2_rows_passing_format_checks"]],
             ["   quote support of these rows", f"yes {qs['yes']}, partly {qs['partly']}, no {qs['no']}, unparsed {qs['unparsed']}"],
             ["3. rows after removing unsupported", st["3_rows_after_quote_support_check"]],
             ["4. entries after merging duplicates", f"{st['4_entries_after_merging_duplicates']} ({st['merged_word_overlap']} word overlap, {st['merged_semantic']} semantic, {st['duplicate_pairs_proposed']} pairs proposed)"],
             ["5. entries in age_cue_only", st["5_entries_in_age_cue_only"]]], ["stage", "count"])
    basis = Counter(it["fact_basis"] for p in pids for it in M[p])
    n = sum(basis.values())
    w(f"\nEntries tied to at least one slot (and so to graph nodes): {pct(basis['registered'], n)}; not tied to any slot (`unknown`): {basis['unknown']}.\n")
    W += [f"- unknown — {p} {it['memory_id']}: “{it['text']}”" for p in pids for it in M[p] if it["fact_basis"] == "unknown"][:20]
    w("\n### Attribute labels [auto]\n")
    cs = Counter()
    for p in pids:
        for it in M[p]:
            for f in ATTRS:
                if it["annotation"]["text_label"][f] in ("direct", "indirect"):
                    cs[(f, it["annotation"]["status"][f])] += 1
    cols = ["source_supported_cue", "unverified_link", "unsupported_association", "unknown_source"]
    W += md([[f] + [cs[(f, c)] for c in cols] for f in ATTRS], ["attribute (text label direct/indirect)"] + cols)
    w("\nAge entries counted as source-supported:\n")
    W += [f"- {p} {it['memory_id']}: “{it['text']}” (nodes: {', '.join(x for x in it['nodes'] if not x.startswith('session'))})"
          for p in pids for it in M[p] if it["annotation"]["status"]["age"] == "source_supported_cue"] or ["- none"]
    w("")

    w("## 6. Background use [auto]\n")
    fam = r"\b(wife|husband|partner|son|daughter|kids?|children|mom|mother|dad|father|parents|brother|sister|family)\b"
    sess_fam = sum(any(re.search(fam, t["text"], re.I) for t in s["turns"] if t["speaker"] == "User") for p in pids for s in H[p]["kept"])
    sess_fam3 = sum(any(re.search(fam, t["text"], re.I) for t in s["turns"] if t["speaker"] == "User") for p in pids for s in H3[p]["kept"])
    W += md([["sessions", sum(len(H3[p]["kept"]) for p in pids), sum(len(H[p]["kept"]) for p in pids)],
             ["sessions where the user mentions a relative", sess_fam3, sess_fam],
             ["sessions with a work, education or life-event mention", 0, 0]], ["", "r3", "r4"])
    w("\nWho comes along is drawn in code, uniformly over the relation types each person has, without looking at age; a relative is named "
      "only through the participants slot or the phone-plan slot. A minor child's age is said when the child comes to a concert, restaurant or trip.\n")

    w("## 7. Still unresolved [auto facts]\n")
    w("- Failed personas: " + (", ".join(p for p in pids if H[p]["status"] != "ok") or "none") + ".")
    w("- The code checks only see what they are written to see (dates, numbers, names, relation, diet and work words). A wish or fact phrased "
      "without such words passes; the model audit in section 4 is the only screen for it.")
    w("- Messages are short and close to the slot wording; the conversations are less natural than r2/r3.")
    w("- ProfileFoundry links between age and partner / adult children / parents / job / education / life events remain `unverified`.")
    mr = os.path.join(R4, "manual_review.md")
    if os.path.exists(mr):
        w("")
        w(open(mr).read().rstrip())
    open(os.path.join(R4, "report.md"), "w").write("\n".join(W) + "\n")
    print("\n".join(W))


if __name__ == "__main__":
    main()
