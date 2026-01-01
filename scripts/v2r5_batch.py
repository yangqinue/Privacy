"""Dataset v2, r5: the r4 design (fact graph + slot generation) made cheaper for batches, tried on 30 personas.

Changes from r4 (see the r4 report for why):
  - assistant messages come from code templates (only user messages are worded by the model);
  - the memory chain is computed in code: an entry is tied to the slots of its cited user message whose required
    words it contains; entries tied to the same slots are merged as repeated occurrences;
  - model-based checks run on fixed random samples only: the r3 session audit (10% of sessions), the quote-support
    check (10% of memory rows), and the SynthPAI attribute labels (20% of entries);
  - two known gaps in the code checks closed: per-unit wording ("each", "per line") and the plan's data is said to be
    the total; request text is turned into the user's own perspective ("their week" -> "your week");
  - personas: u001-u008 as before plus 22 more ProfileFoundry adults, 5 per age group in total;
  - each persona is written as soon as it is finished and skipped on a re-run (--resume).
Wall-clock timings are written to logs/ only (not part of the dataset).

Usage: python scripts/v2r5_batch.py --servers http://localhost:11436=6,http://localhost:11437=6 [--resume]
"""

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import v2r4_preview as G               # graph, slots, plan, code checks (r4)
import v2r4_templates as T4

X, R, P1 = G.X, G.R, G.P1
ATTRS = G.ATTRS
dtext, cseed, as_json = G.dtext, G.cseed, G.as_json
ARGS = None
TIMING = defaultdict(float)
LOG = defaultdict(list)


def log(pid, kind, **kw):
    with P1.LOCK:
        LOG[pid].append({"kind": kind, **kw})


# ------------------------------------------------------------------------------------------- persona selection

def select_30(args):
    """u001-u008 exactly as in r2-r4, then 22 more adults so that each age group has 5: one per household, drawn at
    random within the age group. Partnered adults aged 25-50 without recorded children get 1-2 synthetic minor
    children with probability 0.5 (same age rule as for u007/u008)."""
    base = R.select_profiles(args)
    people = [json.loads(l) for l in open(args.input)]
    by_id = {p["profile_id"]: p for p in people}
    households = defaultdict(list)
    for p in people:
        households[p["household_id"]].append(p["profile_id"])
    used = {b["source"]["household_id"] for b in base}
    need = Counter({g: 5 for g, _, _ in P1.GROUPS}) - Counter(b["fields"]["age_group"]["value"] for b in base)
    rng = random.Random(f"{args.seed}-r5-select")
    cands = sorted(people, key=lambda p: p["profile_id"])
    rng.shuffle(cands)
    extra = []
    for p in cands:
        age = P1.age_on(p["identity"]["dob"])
        g = next((g for g, lo, hi in P1.GROUPS if lo <= age <= hi), None)
        if g and need[g] > 0 and p["household_id"] not in used:
            extra.append(p)
            used.add(p["household_id"])
            need[g] -= 1
    out = list(base)
    for i, p in enumerate(extra):
        pid = f"u{len(base) + i + 1:03d}"
        kids = []
        sp = by_id.get(p["family"].get("spouse"))
        age = P1.age_on(p["identity"]["dob"])
        if sp and sp["household_id"] == p["household_id"] and not p["family"].get("children") and 25 <= age <= 50 and rng.random() < 0.5:
            youngest = min(age, P1.age_on(sp["identity"]["dob"]))
            ages = sorted((rng.randint(0, min(17, youngest - 20)) for _ in range(rng.choice([1, 2]))), reverse=True)
            kids = [{"child_id": f"syn_child_{p['profile_id'][-4:]}_{j + 1}", "age": a, "sex": rng.choice(["girl", "boy"]),
                     "parents": [p["profile_id"], sp["profile_id"]], "lives_with_persona": True, "source": "synthetic",
                     "basis": "r5 rule: partnered, aged 25-50, no recorded children, probability 0.5; 1-2 children, age uniform in "
                              "[0, min(17, younger parent's age - 20)]"} for j, a in enumerate(ages)]
        pr = P1.build_profile(pid, p, by_id, households, kids, random.Random(f"{args.seed}-profile-{pid}"))
        for a in pr["fields"]["co_resident_adults"]["value"]:
            a["gender"] = by_id[a["profile_id"]]["identity"]["gender"]
        out.append(pr)
    return out


# ------------------------------------------------------------------------------------------- assistant templates

ASKQ = {"date": "Which day do you have in mind?", "date_held": "Which date is the show on?", "date_wanted": "Which date would you prefer instead?",
        "date1": "Which days suit you?", "date2": "Which days suit you?", "date_from": "Which dates would you like to travel?",
        "date_to": "Which dates would you like to travel?", "time": "What time works for you?", "participants": "Who will be coming with you?",
        "venue": "Do you have a place in mind?", "class": "Which class would you like to try?", "destination": "Where are you thinking of going?",
        "transport": "How would you like to travel?", "lodging": "What kind of place would you like to stay in?",
        "service": "Which grocery service do you use?", "slot": "Which delivery slot suits you?", "items": "Which items would you like?",
        "carrier": "Which carrier are you with now?", "plan_data": "How much data does your current plan have?",
        "usage": "How much data do you use in a month?", "bill": "How much do you pay each month now?", "reason": "What makes you want to change?",
        "change": "What would you like to change?", "pref_music": "What kind of music do you like?", "pref_seating": "Any seating preference?",
        "pref_schedule": "What time of day suits you best?", "pref_diet": "Any dietary needs I should keep in mind?",
        "pref_hobbies": "Anything you'd like to do there?"}
ACK = ["Got it.", "Sure.", "Okay.", "Thanks."]


def count_phrase(n, what):
    noun = what.split()[0]
    if n == 1:
        noun = {"people": "person", "tickets": "ticket", "travellers": "traveller", "lines": "line"}.get(noun, noun)
    return f"for {n} {noun}"


def phrase(x, said_keys):
    d = lambda v: dt.date.fromisoformat(v)
    k, v = x["key"], x["value"]
    if k.startswith("date"):
        dd = d(v)
        return f"{dd.strftime('%A')}, the {G.ordinal(dd.day)}"
    return {"time": lambda: "around " + x["say"].split("about ")[-1], "count": lambda: count_phrase(v, x.get("what", "people")),
            "participants": lambda: "with " + x["say"].split(": ", 1)[1], "venue": lambda: f"at {v}", "class": lambda: f"a {v} class",
            "destination": lambda: f"going to {v}", "transport": lambda: "by car" if v == "drive" else "by train or bus",
            "lodging": lambda: f"a {v}", "service": lambda: f"through {v}", "slot": lambda: f"{v} delivery",
            "items": lambda: ", ".join(v), "carrier": lambda: f"currently with {v}", "plan_data": lambda: f"current plan {v}",
            "usage": lambda: f"about {v} GB used a month", "bill": lambda: f"about ${v} a month now", "reason": lambda: str(v),
            "change": lambda: "seats closer to the aisle", "pref_music": lambda: " or ".join(v), "pref_seating": lambda: v.replace("prefers", "preferring"),
            "pref_schedule": lambda: v.replace("prefers", "preferring").replace("enjoys", "enjoying"), "pref_diet": lambda: f"{v} options",
            "pref_hobbies": lambda: x["say"].split(": ", 1)[1]}.get(k, lambda: "")()


def assistant_text(S, said_ids, msg, rng):
    if msg.get("asks"):
        nxt = next(x for x in S if x["id"] == msg["asks"])
        q = f"How many {nxt.get('what', 'people')} is it for?" if nxt["key"] == "count" else ASKQ.get(nxt["key"], "Could you tell me a bit more?")
        return f"{rng.choice(ACK)} {q}"
    said = [x for x in S if x["id"] in said_ids and x["key"] != "request"]
    parts = [p for p in (phrase(x, None) for x in said) if p]
    return "Here is what I'll look for: " + "; ".join(parts) + "."


# ------------------------------------------------------------------------------------------- realise (user only)

HOBBY_NEED = {"hiking": r"hik", "board games": r"board|games", "video games": r"video|gam", "gardening": r"garden", "cycling": r"cycl|bik",
              "reading": r"read|book", "cooking": r"cook", "photography": r"photo", "rock climbing": r"climb", "knitting": r"knit",
              "running": r"run", "fishing": r"fish", "yoga": r"yoga", "woodworking": r"wood"}
REL_PLURAL = r"\b(two|three|four|five|six) (sons|daughters|kids|children|brothers|sisters|siblings|parents|of us)\b"


def fix_slots(S, g):
    """r5 fixes on top of the r4 slots (applied to every persona)."""
    for x in S:
        if x["key"] == "request":
            x["say"] = x["say"].replace("their", "your").replace(" them", " you")
        if x["key"] == "plan_data" and g["nodes"]["fact:lines"]["value"] > 1:
            x["say"] += " in total for the whole plan (not per line)"
        if x["key"] == "pref_hobbies":          # was the first five letters of the word, so "cook", "knit", "read" failed
            hobby = x["say"].split(": ", 1)[1]
            x["need"] = [HOBBY_NEED.get(hobby, re.escape(hobby[:4]))]
    return S


def date_phrases(S, ids):
    out = []
    for x in S:
        if x["id"] in ids and x["key"].startswith("date"):
            d = dt.date.fromisoformat(x["value"])
            out.append(f"{d.strftime('%A')}, the {G.ordinal(d.day)}")
    return out


PER_UNIT = r"\beach (line|person|phone|of us)\b|\bper (line|person|phone)\b|\bapiece\b|\bGB each\b"


def realise_session(pr, g, cat, s, S, plan):
    pid = pr["persona_id"]
    turns, said = [], []
    n = int(s["session_id"][1:])
    first = pr["fields"]["given_name"]["value"]
    rng = random.Random(f"{ARGS.seed}-r5ack-{pid}-{s['session_id']}")
    for i, msg in enumerate(plan):
        if msg["speaker"] == "Assistant":
            text = assistant_text(S, said, msg, rng)
            probs = G.check_message(pr, g, cat, s, S, turns, msg, text)
            if probs:
                log(pid, "template_rejected", session=s["session_id"], turn=i + 1, text=text, problems=probs)
                return None, [{"text": text, "problems": probs}], turns
            turns.append({"dia_id": f"D{n}:{i + 1}", "speaker": "Assistant", "text": text, "act": msg.get("act"), "attempts": 1, "template": True})
            continue
        tries = []
        for k in range(4):
            facts = "\n".join(f"- {x['say']}" for x in S if x["id"] in msg["slots"])
            prompt = T4.USER_REALISE_PROMPT.format(name=first, errand=s["errand"].replace("their", "your").replace(" them", " you"),
                                                   conversation=G.render(turns), facts=facts)
            if tries:
                prompt += "\n\nYour previous attempt was rejected because: " + "; ".join(tries[-1]["problems"]) + ". Fix exactly that."
                dp = date_phrases(S, msg["slots"])
                if dp:                  # retries only: spell out the dates (the model kept writing "this Saturday, the 22nd")
                    prompt += " Write the date" + ("s" if len(dp) > 1 else "") + " exactly as: " + "; ".join(f"'{x}'" for x in dp) + \
                        ". Do not mention any other day or date."
                elif any("not registered" in p_ and ("day" in p_ or "weekday" in p_ or "date" in p_) for p_ in tries[-1]["problems"]):
                    prompt += " This message must not mention any day, weekday or date at all."
            try:
                t0 = time.time()
                out, _ = X.ask(ARGS, [{"role": "user", "content": prompt}], cseed(ARGS, pid, "r5real", s["session_id"], i, k), pid,
                               f"realise_{s['session_id']}_{i + 1}_{k}", temperature=0.7 if k == 0 else 0.95)
                TIMING["llm_realise"] += time.time() - t0
                text = R.clean(out)
            except Exception:
                text = ""
            probs = G.check_message(pr, g, cat, s, S, turns, msg, text) if text else ["empty reply"]
            if text and re.search(REL_PLURAL, text, re.I):      # "my two sons" counts relatives listed in the slot
                probs = [p_ for p_ in probs if not p_.startswith("number word not registered")]
            vis = " ".join(x["say"] for x in S if x["id"] in msg["slots"])
            if text and re.search(PER_UNIT, text, re.I) and not re.search(PER_UNIT, vis, re.I):
                probs.append("per-unit wording not registered")
            tries.append({"text": text, "problems": probs})
            if not probs:
                break
        if tries[-1]["problems"]:
            log(pid, "message_failed", session=s["session_id"], turn=i + 1, attempts=tries)
            return None, tries, turns
        if len(tries) > 1:
            log(pid, "message_reworded", session=s["session_id"], turn=i + 1, rejected=tries[:-1])
        said += msg["slots"]
        turns.append({"dia_id": f"D{n}:{i + 1}", "speaker": "User", "text": tries[-1]["text"], "slots": msg["slots"], "attempts": len(tries)})
    return turns, None, turns


# ------------------------------------------------------------------------------------------- memory (code chain)

def build_memory(pr, g, kept, examples, rng):
    pid = pr["persona_id"]
    N = g["nodes"]
    st = Counter()
    slots_by_turn, turns, order = {}, {}, []
    for s in kept:
        for t in s["turns"]:
            turns[t["dia_id"]] = t
            order.append(t["dia_id"])
            slots_by_turn[t["dia_id"]] = [x for x in s["slots"] if x["id"] in t.get("slots", [])]
    n0 = len(P1.LOG[pid])
    t0 = time.time()
    with cf.ThreadPoolExecutor(4) as ex:
        rows = [r for rs in ex.map(lambda s: R.extract_session(ARGS, pid, s, examples), kept) for r in rs]
    TIMING["llm_extract"] += time.time() - t0
    fmt = Counter(e.get("reason") for e in P1.LOG[pid][n0:] if e["kind"] == "memory_row_dropped")
    st["1_rows_returned_by_extraction"] = len(rows) + sum(fmt.values())
    st["2_rows_passing_format_checks"] = len(rows)
    items = []
    for it in rows:
        cand = [x for d in it["dialogue_ids"] for x in slots_by_turn.get(d, []) if x["need"]]
        in_text = [x for x in cand if all(re.search(p, it["text"], re.I) for p in x["need"])]
        quote = " ".join(it["quotes"])
        matched = [x for x in in_text if all(re.search(p, quote, re.I) for p in x["need"])]
        nodes = sorted({nd for x in matched for nd in x["nodes"]})
        if in_text and not matched:
            log(pid, "memory_quote_mismatch", row=it["text"], quote=quote[:160], slots=[x["id"] for x in in_text])
        items.append({**it, "slots": [{"session": it["sessions"][0], "id": x["id"], "key": x["key"], "say": x["say"], "nodes": x["nodes"]} for x in matched],
                      "nodes": nodes, "fact_basis": "registered" if matched else ("quote_mismatch" if in_text else "unknown"),
                      "signature": sorted({(x["key"].rstrip("0123456789"), json.dumps(x["value"])) for x in matched}),
                      "occurrences": [{"session": it["sessions"][0], "date": it["date"], "dia_id": it["dialogue_ids"][0], "quote": it["quotes"][0], "text": it["text"]}]})
    # sampled quote-support check (model), 10% of rows
    sample = [i for i in range(len(items)) if rng.random() < 0.10]

    def sup(i):
        it = items[i]
        cl = [(f"{d}/{x['id']}", x) for d in it["dialogue_ids"] for x in slots_by_turn.get(d, [])]
        prompt = T4.SUPPORT_PROMPT.format(entry=it["text"], scope=it["scope"], plural="s" if len(it["dialogue_ids"]) > 1 else "",
                                          evidence=R.evidence_text(turns, order, it["dialogue_ids"]),
                                          facts="\n".join(f"- {k}: {x['say']}" for k, x in cl) or "- (none)")
        try:
            out, _ = X.ask(ARGS, [{"role": "user", "content": prompt}], cseed(ARGS, pid, "r5sup", i), pid, f"support_{i + 1:03d}", json_mode=True, temperature=0.0)
            return i, str(as_json(out).get("supported", "unparsed"))
        except Exception:
            return i, "unparsed"

    t0 = time.time()
    with cf.ThreadPoolExecutor(4) as ex:
        for i, v in ex.map(sup, sample):
            items[i]["quote_support_sampled"] = v
    TIMING["llm_support_sample"] += time.time() - t0
    # merge: same slot signature, or near-identical wording
    merged, by_sig = [], {}
    for it in items:
        key = json.dumps(it["signature"]) if it["signature"] else None
        w = set(re.findall(r"[a-z0-9']+", it["text"].lower()))
        dup = by_sig.get(key) if key else None
        dup = dup or next((o for o in merged if len(w & o["_w"]) / max(1, len(w | o["_w"])) >= 0.8), None)
        if dup:
            for k in ("dialogue_ids", "quotes", "sessions", "occurrences"):
                dup[k] = dup[k] + [x for x in it[k] if k in ("quotes", "occurrences") or x not in dup[k]]
            dup["scope"] = "stable" if "stable" in (dup["scope"], it["scope"]) else "one_off"
            st["merged_same_slots" if key and by_sig.get(key) is dup else "merged_word_overlap"] += 1
            log(pid, "memory_duplicate_merged", kept=dup["text"], merged=it["text"])
        else:
            o = {**it, "_w": w}
            merged.append(o)
            if key:
                by_sig[key] = o
    final = []
    for i, o in enumerate(merged, 1):
        o.pop("_w")
        o["memory_id"] = f"m{i:03d}"
        o["n_sessions"] = len(set(o["sessions"]))
        o["n_occurrences"] = len(o["occurrences"])
        o["generation_link"] = ({a: max((N[nd]["link"][a] for nd in o["nodes"] if nd in N), key=["independent", "unverified", "co_generated", "direct_source"].index)
                                 for a in ATTRS} if o["nodes"] else {a: "unknown" for a in ATTRS})
        final.append(o)
    st["3_entries_after_merging"] = len(final)
    # sampled SynthPAI labels (model), 20% of entries
    lab = [o for o in final if rng.random() < 0.20]

    def ann(o):
        a = R.annotate(ARGS, pid, o["text"], o["quotes"][0], o["memory_id"], o["generation_link"])
        a["status"] = {f: X.cue_status(a["text_label"][f], o["generation_link"][f], o["fact_basis"]) for f in ATTRS}
        return o, a

    t0 = time.time()
    with cf.ThreadPoolExecutor(4) as ex:
        for o, a in ex.map(ann, lab):
            o["annotation_sampled"] = a
    TIMING["llm_label_sample"] += time.time() - t0
    st["4_entries_in_age_cue_only"] = len(final)   # no slot ever states the user's own age; code rejects unregistered numbers
    return {"raw": final, "stage_counts": dict(st), "format_drops": dict(fmt)}


# ------------------------------------------------------------------------------------------- main

def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--r2", default=os.path.join(ROOT, "data_v2_dialogue_preview_r2"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data_v2_preview_r5_30"))
    ap.add_argument("--input", default=os.path.join(ROOT, "data_v2_preview", "pf", "us_households.jsonl"))
    ap.add_argument("--prev_manifest", default=os.path.join(ROOT, "data_v2_preview", "manifest.json"))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default="qwen3:32b")
    ap.add_argument("--servers", default="http://localhost:11434=1")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--num_ctx", type=int, default=8192)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--memory_only", action="store_true", help="rebuild memory from the saved sessions; sessions are not touched")
    ARGS = X.ARGS = G.ARGS = args = ap.parse_args()
    P1.POOL = G.ServerPool(args.servers)
    t_start = time.time()
    os.makedirs(args.out, exist_ok=True)
    profiles = {p["persona_id"]: p for p in select_30(args)}
    examples = X.T2.fact_examples(json.load(open(os.path.join(ROOT, "external", "upstream_templates", "locomo", "fact_generation_examples_new.json"))))
    for sub in ("graph", "history", "memory", "tasks", "view", "personas", "catalogs", "templates"):
        os.makedirs(os.path.join(args.out, sub), exist_ok=True)
    open(os.path.join(args.out, "templates", "r5__USER_REALISE_PROMPT.txt"), "w").write(T4.USER_REALISE_PROMPT)
    json.dump({"ask": ASKQ, "ack": ACK}, open(os.path.join(args.out, "templates", "r5__assistant_templates.json"), "w"), indent=2)
    tests = G.validator_tests({**profiles}, {p: G.build_graph(profiles[p], json.load(open(os.path.join(args.r2, "catalogs", f"{p}.json"))),
                                                               json.load(open(os.path.join(args.r2, "history", f"{p}.json")))["standing"],
                                                               P1.plan_sessions(random.Random(f"{args.seed}-history-{p}"))) for p in ("u007",)},
                              {"u007": json.load(open(os.path.join(args.r2, "catalogs", "u007.json")))})
    print(f"validator tests: {sum(t['passed'] for t in tests)}/{len(tests)}", flush=True)
    if not all(t["passed"] for t in tests):
        return
    pids = [p for p in sorted(profiles) if not args.only or p in args.only.split(",")]

    def run_memory(pid):
        pr, g = profiles[pid], json.load(open(os.path.join(args.out, "graph", f"{pid}.json")))
        hist = json.load(open(os.path.join(args.out, "history", f"{pid}.json")))
        mem = build_memory(pr, g, hist["kept"], examples, random.Random(f"{args.seed}-r5mem-{pid}")) if hist["kept"] else {"raw": [], "stage_counts": {}, "format_drops": {}}
        json.dump({"persona_id": pid, **mem}, open(os.path.join(args.out, "memory", f"{pid}.json"), "w"), indent=2, ensure_ascii=False)
        print(f"{pid}: memory rebuilt {mem['stage_counts']}", flush=True)
        return pid, hist["status"]

    if args.memory_only:
        with cf.ThreadPoolExecutor(8) as ex:
            res = list(ex.map(run_memory, pids))
        old = json.load(open(os.path.join(args.out, "generation_log.json")))
        for p_ in pids:
            old[p_] = [e for e in old.get(p_, []) if e["kind"] not in ("memory_quote_mismatch", "memory_duplicate_merged")] + LOG.get(p_, [])
        json.dump(old, open(os.path.join(args.out, "generation_log.json"), "w"), indent=2, ensure_ascii=False)
        print("memory rebuilt; new LLM calls:", P1.STATS["llm_calls"])
        return

    def run(pid):
        if args.resume and os.path.exists(os.path.join(args.out, "history", f"{pid}.json")):
            return pid, "skipped"
        t0 = time.time()
        pr = profiles[pid]
        old = os.path.join(args.r2, "catalogs", f"{pid}.json")
        if os.path.exists(old):           # u001-u008: same catalog and standing details as r2-r4
            cat = json.load(open(old))
            standing = json.load(open(os.path.join(args.r2, "history", f"{pid}.json")))["standing"]
        else:
            cat = R.build_catalog(pr, random.Random(f"{args.seed}-catalog-{pid}"))
            standing = R.build_standing(pr, cat, random.Random(f"{args.seed}-standing-{pid}"))
        plan = P1.plan_sessions(random.Random(f"{args.seed}-history-{pid}"))
        g = G.build_graph(pr, cat, standing, plan)
        sessions = []
        for s in plan:
            rng = random.Random(f"{args.seed}-r4slots-{pid}-{s['session_id']}")
            S = fix_slots(G.build_slots(g, pr, s, rng), g)
            sessions.append({**s, "slots": S, "plan": G.make_plan(S, rng)})
        checks = G.graph_checks(g, sessions)
        kept, failed = [], []
        if all(c["ok"] for c in checks):
            with cf.ThreadPoolExecutor(3) as ex:
                for s, (turns, bad, partial) in zip(sessions, ex.map(lambda s: realise_session(pr, g, cat, s, s["slots"], s["plan"]), sessions)):
                    if turns is None:
                        failed.append({"session_id": s["session_id"], "activity": s["activity"], "turn": len(partial) + 1, "attempts": bad})
                    else:
                        kept.append({**s, "turns": turns})
        rng = random.Random(f"{args.seed}-r5sample-{pid}")
        audit = [s for s in kept if rng.random() < 0.10]

        def aud(s):
            d0 = dt.date.fromisoformat(s["date"])
            res = X.check_v3(pr, s, R.public_context(pr, d0, R.persona_at(pr, d0)[1])["text"], G.ctx_from_slots(s["slots"], g["nodes"]), f"r5_{s['session_id']}")
            return s, {k: res[k] for k in ("status", "problems", "claims")}

        t1 = time.time()
        with cf.ThreadPoolExecutor(3) as ex:
            for s, a in ex.map(aud, audit):
                s["llm_audit_sampled"] = a
        TIMING["llm_audit_sample"] += time.time() - t1
        kept.sort(key=lambda s: s["date"])
        hist = {"persona_id": pid, "planned": len(plan), "kept": kept, "failed": failed, "graph_ok": all(c["ok"] for c in checks),
                "activities_covered": sorted({s["activity"] for s in kept}),
                "status": "ok" if len(kept) >= 12 and len({s["activity"] for s in kept}) == 6 else "failed"}
        mem = build_memory(pr, g, kept, examples, random.Random(f"{args.seed}-r5mem-{pid}")) if kept else {"raw": [], "stage_counts": {}, "format_drops": {}}
        tpath = os.path.join(args.r2, "tasks", f"{pid}.json")
        tasks = json.load(open(tpath)) if os.path.exists(tpath) else R.build_tasks(args, pr, cat, random.Random(f"{args.seed}-tasks-{pid}"))
        dump = lambda sub, obj: json.dump(obj, open(os.path.join(args.out, sub, f"{pid}.json"), "w"), indent=2, ensure_ascii=False)
        dump("personas", pr)
        dump("catalogs", cat)
        dump("graph", {**g, "checks": checks})
        dump("tasks", tasks)
        dump("memory", {"persona_id": pid, **mem})
        dump("history", hist)            # written last: its presence marks the persona as finished
        TIMING[f"persona_{pid}"] = time.time() - t0
        print(f"{pid}: {hist['status']} {len(kept)}/{len(plan)} sessions; graph {'ok' if hist['graph_ok'] else 'FAILED'}; memory {mem['stage_counts']}", flush=True)
        return pid, hist["status"]

    with cf.ThreadPoolExecutor(8) as ex:
        res = list(ex.map(run, pids))
    TIMING["total_wall_seconds"] = time.time() - t_start
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    json.dump(dict(TIMING), open(os.path.join(ROOT, "logs", "v2r5_timing.json"), "w"), indent=2)     # local only
    old_log = json.load(open(os.path.join(args.out, "generation_log.json"))) if args.resume and os.path.exists(os.path.join(args.out, "generation_log.json")) else {}
    json.dump({**old_log, **dict(LOG)}, open(os.path.join(args.out, "generation_log.json"), "w"), indent=2, ensure_ascii=False)
    json.dump({"version": "r5 (r4 design, batch settings), 30 personas", "seed": args.seed, "model": args.model,
               "new_llm_calls_last_run": P1.STATS["llm_calls"], "personas": [p for p, _ in res],
               "code_sha256": {f: P1.sha(os.path.join(HERE, f)) for f in ("v2r5_batch.py", "v2r4_preview.py", "v2r4_templates.py", "v2r3_repair.py")}},
              open(os.path.join(args.out, "manifest.json"), "w"), indent=2)
    print("done; new LLM calls:", P1.STATS["llm_calls"], "| statuses:", Counter(s for _, s in res))


if __name__ == "__main__":
    main()
