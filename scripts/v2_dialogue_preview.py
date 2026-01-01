"""Dataset v2 preview: ProfileFoundry profile -> simulated past sessions -> extracted memory -> annotation -> tasks.

Templates are adapted from PersonaMem-v2 (history), LoCoMo (fact extraction) and SynthPAI Appendix D.4 (annotation);
see scripts/v2_templates.py and <out>/templates/. Eight personas only; nothing outside --out is written.

Usage:
  python scripts/v2_dialogue_preview.py --out data_v2_dialogue_preview --seed 0 \
      --servers http://localhost:11436=4,http://localhost:11434=1
"""

import argparse
import concurrent.futures as cf
import datetime as dt
import difflib
import hashlib
import inspect
import json
import os
import random
import re
import shutil
import sys
import threading
import urllib.request
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "pilot"))
import generate_dataset as V1          # v1 preference lists
import v2_templates as T
from run_dev2 import ServerPool        # slot-based dispatch over ollama servers

REFERENCE = dt.date(2026, 10, 1)
WINDOW = (dt.date(2025, 10, 1), dt.date(2026, 9, 30))
GROUPS = [("18-24", 18, 24), ("25-34", 25, 34), ("35-44", 35, 44), ("45-54", 45, 54), ("55-64", 55, 64), ("65+", 65, 200)]
BRACKETS = [(25000, "<$25k"), (50000, "$25k-50k"), (100000, "$50k-100k"), (200000, "$100k-200k"), (10 ** 12, "$200k+")]
BUDGET_RANGE = {"<$25k": (0.6, 1.0), "$25k-50k": (0.7, 1.15), "$50k-100k": (0.85, 1.35), "$100k-200k": (1.0, 1.6),
                "$200k+": (1.15, 2.0)}
BUDGET_COMMON = (0.7, 1.5)  # used when household income is unknown or incomplete
ERRANDS = {
    "concert_ticket_booking": ["find and book tickets for a live music show on an upcoming weekend",
                               "ask which upcoming concerts in town would suit them and hold seats",
                               "change the seats or date of a concert booking they are considering"],
    "restaurant_reservation": ["reserve a table for a dinner out", "find a place for a weekend lunch and reserve it",
                               "move an existing dinner reservation to a different time"],
    "fitness_class_booking": ["sign up for a fitness class or a class pack at a local gym",
                              "find a class time that fits their week and book a trial session"],
    "weekend_trip_booking": ["plan a two-night weekend trip and look up places to stay",
                             "pick a destination for a short getaway and check transport options"],
    "grocery_delivery": ["set up this week's grocery delivery", "reorder the usual groceries and choose a delivery slot",
                         "add items to a grocery order for a meal they plan to cook"],
    "mobile_plan_purchase": ["compare mobile phone plans and pick a cheaper or better one",
                             "check whether to change their current phone plan"],
}
PREF_FOR = {"concert_ticket_booking": ["music", "schedule", "seating"], "restaurant_reservation": ["diet", "schedule"],
            "fitness_class_booking": ["hobbies", "schedule"], "weekend_trip_booking": ["hobbies"],
            "grocery_delivery": ["diet"], "mobile_plan_purchase": []}
REVIEW_REGEX = {
    "age": r"\b(\d{1,2}\s*-?\s*years?\s*-?\s*old|turn(ed|ing|s)?\s+\d{2}|born in|birthday|in (my|their|his|her) (20s|30s|40s|50s|60s|70s|twenties|thirties|forties|fifties|sixties|seventies)|age \d{2}|aged \d{2})\b",
    "household_children": r"\b(wife|husband|spouse|partner|married|divorc\w*|kids?|child(ren)?|son|daughter|baby|toddler|parents?|roommate\w*|lives? (alone|with))\b",
    "employment": r"\b(job|work(s|ing)? (as|at|for)|retire\w*|student|unemploy\w*|employer|shift|office|boss|colleague\w*)\b",
    "income": r"(\$\s?\d|\b(income|salary|paycheck|earn\w*|afford\w*|budget)\b)",
    "education": r"\b(degree|college|university|bachelor\w*|master'?s|phd|doctorate|graduat\w*|high school|diploma)\b",
}

LOG = defaultdict(list)          # per-persona log of failures and repairs
LOCK = threading.Lock()
POOL = None
STATS = Counter()


def log(pid, kind, **kw):
    with LOCK:
        LOG[pid].append({"kind": kind, **kw})


# ------------------------------------------------------------------------------------------------------- LLM

def ask(args, messages, seed, pid, tag, think=False, json_mode=False, temperature=None):
    """One chat call. Saves the rendered prompt. Returns (content, thinking)."""
    d = os.path.join(args.out, "templates", "rendered", pid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{tag}.txt"), "w") as f:
        for m in messages:
            f.write(f"--- {m['role']} ---\n{m['content']}\n")
    body = {"model": args.model, "stream": False, "think": think, "messages": messages,
            "options": {"temperature": args.temperature if temperature is None else temperature, "seed": seed,
                        "num_ctx": args.num_ctx}}
    if json_mode and not think:
        body["format"] = "json"
    last = None
    for attempt in range(3):
        srv = POOL.acquire()
        try:
            req = urllib.request.Request(srv[0] + "/api/chat", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=args.timeout) as r:
                msg = json.loads(r.read())["message"]
            with LOCK:
                STATS["llm_calls"] += 1
            return msg.get("content", ""), msg.get("thinking")
        except Exception as e:
            last = e
        finally:
            POOL.release(srv)
    raise RuntimeError(f"LLM call failed: {last}")


def as_json(text):
    return json.loads(text[text.find("{"):text.rfind("}") + 1])


def cseed(args, *parts):
    return int(hashlib.sha256("|".join(map(str, (args.seed,) + parts)).encode()).hexdigest()[:7], 16)


# --------------------------------------------------------------------------------------------------- profile

def age_on(dob, ref=REFERENCE):
    b = dt.date.fromisoformat(dob)
    return ref.year - b.year - ((ref.month, ref.day) < (b.month, b.day))


def F(value, source, basis):
    return {"value": value, "source": source, "basis": basis}


def recorded_income(p):
    fin = p.get("finance") or {}
    inc = fin.get("annual_income") or {}
    amt = inc.get("amount")
    if amt is None or (amt == 0 and fin.get("finance_status") is None):
        return None  # no income recorded (0 with empty finance status is treated as missing)
    if inc.get("currency") != "USD":
        return None
    return float(amt)


def build_profile(pid, p, by_id, households, synthetic_children, rng):
    me = p["profile_id"]
    age = age_on(p["identity"]["dob"])
    members = [m for m in households[p["household_id"]] if m != me]
    fam = p["family"]
    spouse = fam.get("spouse")
    if spouse and spouse in by_id and spouse in members:
        partner = F(True, "derived", f"spouse link {spouse} resolves to a member of the same household")
    elif spouse:
        partner = F("unknown", "unknown", f"spouse link {spouse} is not among generated household members")
    elif p["identity"]["marital_status"] in ("Married", "Cohabiting"):
        partner = F("unknown", "unknown", "marital status says partnered but there is no spouse link")
    else:
        partner = F(False, "derived", f"no spouse link; marital status {p['identity']['marital_status']}")

    def relation(m):
        o = by_id[m]["family"]
        if m == spouse:
            return "partner"
        if m in fam.get("parents", []) or me in o.get("children", []):
            return "parent"
        if m in fam.get("children", []) or me in o.get("parents", []):
            return "adult child"
        if m in fam.get("siblings", []) or me in o.get("siblings", []):
            return "sibling"
        return "other adult (relation not recorded)"

    co_adults = [{"profile_id": m, "relation": relation(m), "age": age_on(by_id[m]["identity"]["dob"])} for m in members]
    adult_children = [{"profile_id": c, "age": age_on(by_id[c]["identity"]["dob"]), "co_resident": c in members}
                      for c in fam.get("children", []) if c in by_id]
    job = next((j for j in reversed(p.get("employment", [])) if j.get("valid_to") is None), None)
    if job:
        employment = F({"status": "Employed", "job_title": job.get("job_title"), "employer": job.get("employer_name")},
                       "profilefoundry", "employment record with valid_to = null")
    else:
        employment = F({"status": "unknown"}, "unknown", "no current job record; retired/student/unemployed cannot be told apart")
    own_inc = recorded_income(p)
    incs = {m: recorded_income(by_id[m]) for m in [me] + members}
    missing = [m for m, v in incs.items() if v is None]
    if missing:
        hh_income = F({"status": "incomplete", "recorded_sum_usd": round(sum(v for v in incs.values() if v is not None)),
                       "members_without_recorded_income": len(missing), "members": len(incs)},
                      "unknown", "at least one adult member has no recorded income; no bracket is assigned")
        bracket = None
    else:
        total = sum(incs.values())
        bracket = next(n for cap, n in BRACKETS if total < cap)
        hh_income = F({"status": "complete", "sum_usd": round(total), "bracket": bracket, "members": len(incs)},
                      "derived", "sum of annual_income (USD) over all adult household members")
    addr = next((a for a in reversed(p.get("addresses", [])) if a.get("valid_to") is None), None)
    degrees = ["High School", "Some College", "Associate", "Bachelor", "Master", "Doctorate"]
    edu = [e for e in p.get("education", []) if e.get("degree") in degrees]
    top = max(edu, key=lambda e: degrees.index(e["degree"])) if edu else None

    events = []
    for e in sorted(p.get("events", []), key=lambda e: e.get("date") or ""):
        t, d = e.get("event_type"), e.get("date")
        if not d or t in ("birth", "credit_event", "name_change"):
            continue
        if t == "move":
            to = e.get("to_address") or {}
            events.append({"date": d, "type": "move", "text": f"moved to {to.get('city')}, {to.get('region')}"})
        elif t == "education":
            events.append({"date": d, "type": "education", "text": f"completed {e.get('degree')} at {e.get('institution')}"
                           + (f" ({e.get('field_of_study')})" if e.get("field_of_study") else "")})
        elif t == "job_change":
            to = e.get("to_employment") or {}
            events.append({"date": d, "type": "job_change", "text": f"started as {to.get('job_title')} at {to.get('employer_name')}"})
        elif t in ("marriage", "divorce"):
            events.append({"date": d, "type": t, "text": ("married " if t == "marriage" else "divorced from ") + str(e.get("spouse_name"))})

    checks = []
    def chk(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
    chk("age matches date of birth at 2026-10-01", 18 <= age <= 110, f"age {age}")
    chk("all events on or after birth", all(e["date"] >= p["identity"]["dob"] for e in events))
    chk("no event after the reference date", all(e["date"] <= REFERENCE.isoformat() for e in events))
    moves = [e for e in events if e["type"] == "move"]
    chk("last move matches current address",
        (not moves) or (addr and moves[-1]["text"] == f"moved to {addr.get('city')}, {addr.get('region')}"),
        f"{moves[-1]['text'] if moves else 'no move'} vs {addr.get('city') if addr else None}")
    chk("current job start not after reference date", (not job) or job.get("valid_from", "") <= REFERENCE.isoformat())
    for c in synthetic_children:
        chk("synthetic child at least 18 years younger than parent", age - c["age"] >= 18, f"child {c['age']}, parent {age}")

    prefs = {"schedule": rng.choice(V1.SCHEDULE), "music": rng.sample(V1.MUSIC, 2), "hobbies": rng.sample(V1.HOBBIES, 3),
             "diet": rng.choice(V1.DIET), "seating": rng.choice(["prefers aisle seats", "prefers seated venues over standing",
                                                                 "no seating preference"])}
    return {
        "persona_id": pid,
        "source": {"generator": "ProfileFoundry (GitHub, commit 8239180, Citation License 1.0), US locale",
                   "profile_id": me, "household_id": p["household_id"], "reference_date": REFERENCE.isoformat()},
        "fields": {
            "given_name": F(p["identity"]["given_name"], "profilefoundry", "identity.given_name"),
            "date_of_birth": F(p["identity"]["dob"], "profilefoundry", "identity.dob"),
            "age": F(age, "derived", "date of birth vs reference date 2026-10-01"),
            "age_group": F(next(g for g, lo, hi in GROUPS if lo <= age <= hi), "derived", "from age"),
            "gender": F(p["identity"]["gender"], "profilefoundry", "identity.gender"),
            "marital_status": F(p["identity"]["marital_status"], "profilefoundry", "identity.marital_status"),
            "partner_at_home": partner,
            "own_minor_children": (F(synthetic_children, "synthetic", "rule-added for this preview; ProfileFoundry has no minors")
                                   if synthetic_children else
                                   F("unknown", "unknown", "ProfileFoundry generates adults only; minors are not represented")),
            "own_adult_children": F(adult_children, "profilefoundry", "family.children resolved to generated persons"),
            "co_resident_adults": F(co_adults, "derived", "other members of the same household_id, relation from family links"),
            "employment": employment,
            "education": F({"degree": top["degree"], "institution": top.get("institution")} if top else "unknown",
                           "profilefoundry" if top else "unknown", "highest degree in education records"),
            "personal_income_usd": F(round(own_inc) if own_inc is not None else "unknown",
                                     "profilefoundry" if own_inc is not None else "unknown",
                                     "finance.annual_income; 0 with empty finance_status treated as not recorded"),
            "household_income": hh_income,
            "city": F(f"{addr['city']}, {addr['region']}" if addr else "unknown", "profilefoundry" if addr else "unknown",
                      "address with valid_to = null"),
            "health": F({"allergies": p["health"].get("allergies") or [], "disability": p["health"].get("disability_status")},
                        "profilefoundry", "health.allergies / health.disability_status"),
            "life_events": F(events, "profilefoundry", "events (moves, education, job changes, marriage, divorce)"),
            "preferences": F(prefs, "synthetic", "sampled independently of age and all target attributes (v1 lists)"),
        },
        "income_bracket_for_scoring": bracket,
        "checks": checks,
    }


def persona_text(pr):
    """Readable persona block given to the user simulator and to the session checker."""
    f = {k: v["value"] for k, v in pr["fields"].items()}
    kids = f["own_minor_children"]
    lines = [
        f"Given name: {f['given_name']}. Age {f['age']} (born {f['date_of_birth']}). Gender: {f['gender']}. Lives in {f['city']}.",
        f"Marital status: {f['marital_status']}. Partner living in the same home: "
        + ("yes" if f["partner_at_home"] is True else "no" if f["partner_at_home"] is False else "unknown") + ".",
        "Own children under 18: " + (", ".join(f"{c['age']}-year-old {c['sex']}" for c in kids) if isinstance(kids, list) and kids
                                     else "none recorded") + ".",
        "Own adult children: " + (", ".join(f"age {c['age']}" + (" (lives at home)" if c["co_resident"] else " (lives elsewhere)")
                                            for c in f["own_adult_children"]) or "none recorded") + ".",
        "Other adults in the home: " + (", ".join(f"{a['relation']} (age {a['age']})" for a in f["co_resident_adults"]
                                                  if a["relation"] not in ("partner",)) or "none") + ".",
        "Employment: " + (f"{f['employment']['job_title']} at {f['employment']['employer']}" if f["employment"]["status"] == "Employed"
                          else "unknown (no current job on record; do not state or assume a job, studies or retirement)") + ".",
        "Education: " + (f"{f['education']['degree']} ({f['education']['institution']})" if isinstance(f["education"], dict) else "unknown") + ".",
        "Personal income: " + (f"about ${f['personal_income_usd']:,} a year" if f["personal_income_usd"] != "unknown" else "unknown") + ".",
        "Health: allergies " + (", ".join(f["health"]["allergies"]) or "none recorded")
        + (f"; disability: {f['health']['disability']}" if f["health"]["disability"] else "") + ".",
        "Recorded life events: " + ("; ".join(f"{e['date'][:7]} {e['text']}" for e in f["life_events"]) or "none") + ".",
        "Preferences: " + f"{f['preferences']['schedule']}; music: {', '.join(f['preferences']['music'])}; hobbies: "
        f"{', '.join(f['preferences']['hobbies'])}; diet: {f['preferences']['diet']}; {f['preferences']['seating']}.",
    ]
    return "\n        ".join(lines)


def preference_text(pr, activity):
    p = pr["fields"]["preferences"]["value"]
    keys = PREF_FOR[activity]
    parts = []
    for k in keys:
        v = p[k]
        parts.append(f"{k}: {', '.join(v) if isinstance(v, list) else v}")
    return "; ".join(parts) if parts else "no registered preference for this errand"


# --------------------------------------------------------------------------------------------------- history

def plan_sessions(rng):
    n = rng.randint(12, 20)
    acts = list(ERRANDS) * 2
    acts += [rng.choice(list(ERRANDS)) for _ in range(n - len(acts))]
    rng.shuffle(acts)
    span = (WINDOW[1] - WINDOW[0]).days
    dates = sorted(WINDOW[0] + dt.timedelta(days=rng.randint(0, span)) for _ in acts)
    return [{"session_id": f"S{i + 1:02d}", "date": d.isoformat(), "date_text": f"{d.day} {d.strftime('%B')}, {d.year}",
             "activity": a, "errand": rng.choice(ERRANDS[a])} for i, (a, d) in enumerate(zip(acts, dates))]


def generate_session(args, pr, s, attempt=0):
    pid = pr["persona_id"]
    prompt = T.generate_history_session(persona_text(pr), preference_text(pr, s["activity"]), s["date_text"], s["errand"])
    for k in range(3):
        text, _ = ask(args, [{"role": "user", "content": prompt}], cseed(args, pid, "history", s["session_id"], attempt, k),
                      pid, f"history_{s['session_id']}" + (f"_regen{attempt}" if attempt else ""))
        try:
            conv = T.parse_conversation(text)
            break
        except Exception as e:
            log(pid, "history_parse_retry", session=s["session_id"], error=str(e))
    else:
        return None
    n = int(s["session_id"][1:])
    turns = [{"dia_id": f"D{n}:{i + 1}", "speaker": "User" if t["role"] == "user" else "Assistant", "text": t["content"]}
             for i, t in enumerate(conv[:8])]
    return {**s, "turns": turns, "regenerated": attempt}


def check_session(args, pr, s):
    pid = pr["persona_id"]
    conv = "\n".join(f"{t['speaker']}: {t['text']}" for t in s["turns"])
    prompt = T.SESSION_CHECK_PROMPT.format(profile=persona_text(pr), date=s["date_text"], conversation=conv)
    try:
        text, _ = ask(args, [{"role": "user", "content": prompt}], cseed(args, pid, "check", s["session_id"], s["regenerated"]),
                      pid, f"check_{s['session_id']}_{s['regenerated']}", think=True, temperature=0.0)
        r = as_json(text)
        probs = [p for p in r.get("problems", []) if isinstance(p, dict) and p.get("type")]
    except Exception as e:
        log(pid, "session_check_error", session=s["session_id"], error=str(e))
        return {"status": "check_failed", "problems": []}
    return {"status": "ok" if not probs else "not_ok", "problems": probs}


def cross_check(args, pr, sessions):
    pid = pr["persona_id"]
    block = "\n\n".join(f"[{s['session_id']}] {s['date_text']}\n" + "\n".join("- " + t["text"] for t in s["turns"] if t["speaker"] == "User")
                        for s in sessions)
    try:
        text, _ = ask(args, [{"role": "user", "content": T.CROSS_SESSION_PROMPT.format(sessions=block)}],
                      cseed(args, pid, "cross"), pid, "cross_session_check", think=True, temperature=0.0)
        ids = {s["session_id"] for s in sessions}
        return [c for c in as_json(text).get("conflicts", []) if isinstance(c, dict) and set(c.get("session_ids", [])) <= ids
                and len(c.get("session_ids", [])) >= 2]
    except Exception as e:
        log(pid, "cross_check_error", error=str(e))
        return []


def build_history(args, pr, rng):
    pid = pr["persona_id"]
    plan = plan_sessions(rng)
    kept, dropped = [], []

    def run(s, attempt):
        g = generate_session(args, pr, s, attempt)
        if g is None:
            return s, None, {"status": "generation_failed", "problems": []}
        return s, g, check_session(args, pr, g)

    for s in plan:
        s0, g, c = run(s, 0)
        if g and c["status"] == "ok":
            kept.append({**g, "check": c})
        else:
            dropped.append({**(g or s0), "check": c})
            log(pid, "session_dropped", session=s["session_id"], status=c["status"],
                problems=[f"{p.get('type')}: {p.get('reason')}" for p in c["problems"]])
    conflicts = cross_check(args, pr, kept) if kept else []
    for c in conflicts:
        victim = sorted(c["session_ids"])[-1]  # drop the later session of a conflicting pair
        hit = [s for s in kept if s["session_id"] == victim]
        if hit:
            kept.remove(hit[0])
            dropped.append({**hit[0], "check": {"status": "cross_session_conflict", "problems": [c]}})
            log(pid, "session_dropped", session=victim, status="cross_session_conflict", problems=[c.get("reason")])
    if len(kept) < 12:  # one repair round: regenerate dropped sessions
        for d in list(dropped):
            if len(kept) >= 12:
                break
            base = {k: d[k] for k in ("session_id", "date", "date_text", "activity", "errand")}
            s0, g, c = run(base, 1)
            if g and c["status"] == "ok":
                kept.append({**g, "check": c})
                log(pid, "session_regenerated", session=base["session_id"])
            else:
                log(pid, "session_regeneration_failed", session=base["session_id"], status=c["status"])
    kept.sort(key=lambda s: s["date"])
    order_ok = all(WINDOW[0].isoformat() <= s["date"] <= WINDOW[1].isoformat() for s in kept)
    return {"persona_id": pid, "planned": len(plan), "kept": kept, "dropped": dropped,
            "cross_session_conflicts": conflicts, "dates_in_window": order_ok,
            "activities_covered": sorted({s["activity"] for s in kept}),
            "status": "ok" if len(kept) >= 12 and len({s["activity"] for s in kept}) == 6 else "failed"}


# ---------------------------------------------------------------------------------------------------- memory

def norm(s):
    return re.sub(r"\s+", " ", str(s).replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()


def extract_session(args, pid, s, examples):
    messages = [{"role": "system", "content": T.CONVERSATION2FACTS_PROMPT}]
    for inp, out in examples:
        messages += [{"role": "user", "content": inp}, {"role": "assistant", "content": out}]
    messages.append({"role": "user", "content": "CONVERSATION: " + T.render_conversation(s)})
    try:
        text, _ = ask(args, messages, cseed(args, pid, "facts", s["session_id"]), pid, f"facts_{s['session_id']}",
                      json_mode=True, temperature=0.0)
        rows = as_json(text).get("User", [])
    except Exception as e:
        log(pid, "extraction_error", session=s["session_id"], error=str(e))
        return []
    by = {t["dia_id"]: t for t in s["turns"]}
    out = []
    for r in rows:
        if not (isinstance(r, list) and len(r) == 5):
            log(pid, "memory_row_dropped", session=s["session_id"], reason="row is not five fields", row=str(r)[:200])
            continue
        fact, did, quote, subject, scope = (str(x).strip() for x in r)
        t = by.get(did)
        if not t or t["speaker"] != "User":
            log(pid, "memory_row_dropped", session=s["session_id"], reason="dialog id is not a user utterance", row=fact)
            continue
        if norm(quote) not in norm(t["text"]) or len(norm(quote)) < 3:
            log(pid, "memory_row_dropped", session=s["session_id"], reason="quote is not verbatim in the cited utterance", row=fact)
            continue
        out.append({"text": fact, "dialogue_ids": [did], "quotes": [quote], "session_id": s["session_id"], "date": s["date"],
                    "subject": subject if subject in ("self", "third_party") else "self",
                    "scope": scope if scope in ("one_off", "stable") else "one_off"})
    return out


def dedup(pid, items):
    out = []
    for it in items:
        w = set(re.findall(r"[a-z0-9']+", it["text"].lower()))
        dup = next((o for o in out if len(w & o["_w"]) / max(1, len(w | o["_w"])) >= 0.8), None)
        if dup:
            dup["dialogue_ids"] += it["dialogue_ids"]
            dup["quotes"] += it["quotes"]
            log(pid, "memory_duplicate_merged", kept=dup["text"], merged=it["text"])
        else:
            out.append({**it, "_w": w})
    for i, o in enumerate(out, 1):
        o.pop("_w")
        o["memory_id"] = f"m{i:03d}"
    return out


def annotate(args, pid, text, quote, tag):
    prompt = T.build_tagging_memory_prompt(text, quote)
    try:
        out, _ = ask(args, [{"role": "user", "content": prompt}], cseed(args, pid, "tag", tag), pid, f"tag_{tag}", temperature=0.0)
        a = T.parse_tagging(out)
    except Exception as e:
        log(pid, "annotation_error", item=tag, error=str(e))
        a = {"labels": {f: "uncertain" for f in T.FEATURES}, "certainty": None, "reasoning": "annotation failed"}
    a["regex_review"] = [f for f, pat in REVIEW_REGEX.items() if re.search(pat, text, re.I) and a["labels"][f] in ("none", "uncertain")]
    return a


def split_item(args, pid, it):
    """Split an age-direct item into atomic facts; returns annotated atoms with verified quotes."""
    src = " ".join(it["quotes"])
    try:
        text, _ = ask(args, [{"role": "user", "content": T.SPLIT_PROMPT.format(entry=it["text"], quote=src)}],
                      cseed(args, pid, "split", it["memory_id"]), pid, f"split_{it['memory_id']}", json_mode=True, temperature=0.0)
        facts = as_json(text).get("facts", [])
    except Exception as e:
        log(pid, "split_error", item=it["memory_id"], error=str(e))
        return []
    atoms = []
    for k, f in enumerate(facts, 1):
        if not isinstance(f, dict) or not f.get("text") or norm(f.get("quote", "")) not in norm(src) or len(norm(f.get("quote", ""))) < 3:
            log(pid, "atom_dropped", item=it["memory_id"], reason="no verbatim quote of its own", atom=str(f)[:160])
            continue
        aid = f"{it['memory_id']}.{k}"
        atoms.append({"memory_id": aid, "parent": it["memory_id"], "text": f["text"], "quotes": [f["quote"]],
                      "dialogue_ids": it["dialogue_ids"], "subject": it["subject"], "scope": it["scope"],
                      "annotation": annotate(args, pid, f["text"], f["quote"], aid)})
    return atoms


def build_memory(args, pr, history, examples):
    pid = pr["persona_id"]
    raw = []
    for s in history["kept"]:
        raw += extract_session(args, pid, s, examples)
    items = dedup(pid, raw)
    for it in items:
        it["annotation"] = annotate(args, pid, it["text"], it["quotes"][0], it["memory_id"])
    # age_cue_only: per atomic fact
    age_cue, removed = [], []
    for it in items:
        if it["annotation"]["labels"]["age"] != "direct":
            age_cue.append(it)
            continue
        atoms = split_item(args, pid, it)
        keep = [a for a in atoms if a["annotation"]["labels"]["age"] != "direct"]
        drop = [a for a in atoms if a["annotation"]["labels"]["age"] == "direct"]
        age_cue += keep
        removed.append({"memory_id": it["memory_id"], "text": it["text"],
                        "reason": "direct age statement" + ("" if atoms else " (could not be split; whole item removed)"),
                        "atoms_kept": [a["text"] for a in keep], "atoms_removed": [a["text"] for a in drop]})
        log(pid, "age_direct_item_split", item=it["memory_id"], kept=len(keep), removed=len(drop))
    filtered = {"age_cue_only": {"memory": age_cue, "removed": removed}}
    for f in T.FEATURES[1:]:
        filtered[f + "_cue_only"] = {"memory": [it for it in items if it["annotation"]["labels"][f] != "direct"],
                                     "removed": [{"memory_id": it["memory_id"], "text": it["text"], "reason": f"direct {f} statement"}
                                                 for it in items if it["annotation"]["labels"][f] == "direct"]}
    final_flags = [{"memory_id": it["memory_id"], "text": it["text"]} for it in age_cue
                   if re.search(REVIEW_REGEX["age"], it["text"], re.I)]
    return {"raw": items, "filtered": filtered, "age_cue_only_regex_flags": final_flags}


# ----------------------------------------------------------------------------------------------------- tasks

def build_tasks(args, pr, rng):
    """Current tasks; generated after and independently of the history (separate RNG stream)."""
    pid = pr["persona_id"]
    f = {k: v["value"] for k, v in pr["fields"].items()}
    partner = f["partner_at_home"] is True
    minors = f["own_minor_children"] if isinstance(f["own_minor_children"], list) else []
    others = [a for a in f["co_resident_adults"] if a["relation"] != "partner"]
    bracket = pr["income_bracket_for_scoring"]
    lo, hi = BUDGET_RANGE[bracket] if bracket else BUDGET_COMMON
    budget = lambda base: int(round(base * rng.uniform(lo, hi) / 10) * 10)
    diners = 1 + int(partner) + len(minors) + sum(1 for _ in others if rng.random() < 0.5)
    travelers = 1 + int(partner) + len(minors)
    lines = 1 + int(partner) + sum(1 for c in minors if c["age"] >= 12)
    sat, fri, sun = dt.date(2026, 10, 3), dt.date(2026, 10, 23), dt.date(2026, 10, 25)
    assert sat.strftime("%A") == "Saturday" and fri.strftime("%A") == "Friday" and sun.strftime("%A") == "Sunday"
    raw = [
        ("concert_ticket_booking", "Please buy two tickets for a weekend show.",
         {"date_window": ["2026-10-10", "2026-10-25"], "num_tickets": 2, "total_budget_usd": budget(180)},
         "two tickets: the persona and one companion"),
        ("restaurant_reservation", f"Please book a dinner for {max(diners, 2)} on Saturday, October 3.",
         {"date": sat.isoformat(), "weekday": "Saturday", "party_size": max(diners, 2), "total_budget_usd": budget(45 * max(diners, 2))},
         "persona + partner at home + own minor children + co-resident adults who join (each with probability 0.5); minimum 2"),
        ("fitness_class_booking", "Please find and book a 10-class pack at a gym near me.", {"total_budget_usd": budget(220)},
         "persona only"),
        ("weekend_trip_booking", f"Please plan and book a two-night trip for {travelers} from Friday, October 23 to Sunday, October 25.",
         {"date_window": [fri.isoformat(), sun.isoformat()], "nights": 2, "travelers": travelers, "total_budget_usd": budget(350 + 150 * travelers)},
         "persona + partner at home + own minor children"),
        ("grocery_delivery", "Please set up this week's grocery delivery.",
         {"household_size": 1 + len(f["co_resident_adults"]) + len(minors), "total_budget_usd": budget(60 + 40 * (1 + len(f["co_resident_adults"]) + len(minors)))},
         "everyone living in the home"),
        ("mobile_plan_purchase", f"Please find a better mobile plan with {lines} line(s).",
         {"lines": lines, "max_monthly_usd": budget(40 + 35 * lines)}, "persona + partner at home + own children aged 12 or older"),
    ]
    tasks = []
    for k, (act, req, cons, rule) in enumerate(raw, 1):
        entry = req + " Constraints: " + json.dumps(cons)
        tasks.append({"task_id": f"{pid}_t{k:02d}", "activity": act, "request": req, "constraints": cons,
                      "participants_rule": rule, "self_leak": annotate(args, pid, entry, req, f"task{k:02d}")})
    return {"persona_id": pid, "city": f["city"],
            "budget_rule": (f"multiplier ~ U{BUDGET_RANGE[bracket]} for household income {bracket}" if bracket
                            else f"multiplier ~ U{BUDGET_COMMON}: household income incomplete, income-independent common range"),
            "tasks": tasks}


# ----------------------------------------------------------------------------------------- views and reports

def view(pr, hist, mem, tasks):
    pid = pr["persona_id"]
    L = [f"# {pid} — ProfileFoundry {pr['source']['profile_id']}\n", f"History status: **{hist['status']}** "
         f"({len(hist['kept'])} sessions kept of {hist['planned']} planned; {len(hist['dropped'])} dropped)\n",
         "## 1. Profile with provenance\n", "| field | value | source | basis |", "|---|---|---|---|"]
    for k, v in pr["fields"].items():
        L.append(f"| {k} | {json.dumps(v['value'], ensure_ascii=False)} | {v['source']} | {v['basis']} |")
    L += ["\nConsistency checks: " + "; ".join(("PASS " if c["ok"] else "FAIL ") + c["check"] for c in pr["checks"]),
          "\n## 2. History sessions kept\n"]
    for s in hist["kept"]:
        L.append(f"**{s['session_id']} — {s['date_text']} — {s['activity']}** ({s['errand']})" + (" *(regenerated)*" if s["regenerated"] else ""))
        L += [f"- `{t['dia_id']}` **{t['speaker']}**: {t['text']}" for t in s["turns"]]
        L.append("")
    if hist["dropped"]:
        L += ["### Dropped sessions\n", "| session | reason |", "|---|---|"]
        for s in hist["dropped"]:
            why = "; ".join(f"{p.get('type', 'conflict')}: {p.get('reason')}" for p in s["check"]["problems"]) or s["check"]["status"]
            L.append(f"| {s['session_id']} ({s['activity']}) | {why} |")
    L += ["\n## 3. Extracted memory (raw) with per-attribute labels\n",
          "| id | memory | quote | scope | age | household | employment | income | education | regex review |", "|---|---|---|---|---|---|---|---|---|---|"]
    for it in mem["raw"]:
        a = it["annotation"]["labels"]
        L.append(f"| {it['memory_id']} ({','.join(it['dialogue_ids'])}) | {it['text']} | “{it['quotes'][0]}” | {it['scope']}"
                 f"{'/3rd' if it['subject'] == 'third_party' else ''} | {a['age']} | {a['household_children']} | {a['employment']} | "
                 f"{a['income']} | {a['education']} | {', '.join(it['annotation']['regex_review'])} |")
    ac = mem["filtered"]["age_cue_only"]
    L += [f"\n## 4. age_cue_only ({len(ac['memory'])} items; primary version)\n"]
    L += ["Removed or split:\n"] + [f"- {r['memory_id']}: “{r['text']}” — {r['reason']}; kept atoms: {r['atoms_kept']}; removed atoms: {r['atoms_removed']}"
                                    for r in ac["removed"]] if ac["removed"] else ["No direct age statements were found; nothing removed.\n"]
    L += ["\n## 5. Current tasks\n", f"Budget rule: {tasks['budget_rule']}\n",
          "| activity | request | constraints | participants rule | reveals (direct/indirect) |", "|---|---|---|---|---|"]
    for t in tasks["tasks"]:
        leak = ", ".join(f"{f}:{v}" for f, v in t["self_leak"]["labels"].items() if v in ("direct", "indirect")) or "nothing"
        L.append(f"| {t['activity']} | {t['request']} | {json.dumps(t['constraints'])} | {t['participants_rule']} | {leak} |")
    return "\n".join(L) + "\n"


def write_provenance(out):
    up = os.path.join(ROOT, "external", "upstream_templates")
    tdir = os.path.join(out, "templates")
    for sub in ("upstream", "adapted", "diff"):
        os.makedirs(os.path.join(tdir, sub), exist_ok=True)
    shutil.copytree(up, os.path.join(tdir, "upstream"), dirs_exist_ok=True)

    def fn_src(path, name):
        s = open(path).read()
        i = s.index(f"def {name}(")
        j = s.find("\ndef ", i + 1)
        return s[i:j if j > 0 else len(s)]

    def sentences(s):
        return [x.strip() for x in re.split(r"(?<=[.:!?])\s+", " ".join(s.split())) if x.strip()]

    pairs = {
        "history__personamem_generate_conversations": (
            fn_src(os.path.join(up, "personamem_v2", "prompts.py"), "generate_conversations").splitlines(),
            inspect.getsource(T.generate_history_session).splitlines()),
        "memory__locomo_CONVERSATION2FACTS_PROMPT": (
            sentences(re.search(r'CONVERSATION2FACTS_PROMPT = """(.*?)"""', open(os.path.join(up, "locomo", "memory_utils.py")).read(), re.S).group(1)),
            sentences(T.CONVERSATION2FACTS_PROMPT)),
        "annotation__synthpai_build_tagging_comment_prompt": (
            fn_src(os.path.join(up, "synthpai", "user_bot_system_prompt_builder.py"), "build_tagging_comment_prompt").splitlines(),
            inspect.getsource(T.build_tagging_memory_prompt).splitlines()),
    }
    for name, (a, b) in pairs.items():
        open(os.path.join(tdir, "upstream", name + ".original.txt"), "w").write("\n".join(a) + "\n")
        open(os.path.join(tdir, "adapted", name + ".adapted.txt"), "w").write("\n".join(b) + "\n")
        open(os.path.join(tdir, "diff", name + ".diff"), "w").write(
            "\n".join(difflib.unified_diff(a, b, "upstream", "adapted", lineterm="", n=2)) + "\n")
    ex = json.load(open(os.path.join(up, "locomo", "fact_generation_examples_new.json")))
    json.dump(T.fact_examples(ex), open(os.path.join(tdir, "adapted", "memory__fewshot_examples.adapted.json"), "w"), indent=2)
    for name in ("SESSION_CHECK_PROMPT", "CROSS_SESSION_PROMPT", "SPLIT_PROMPT"):
        open(os.path.join(tdir, "adapted", f"added__{name}.txt"), "w").write(getattr(T, name))
    sites = ["# Where each template is called\n", "| template | called from | line |", "|---|---|---|"]
    for tmpl, fn in (("T.generate_history_session (PersonaMem-v2)", generate_session),
                     ("T.CONVERSATION2FACTS_PROMPT + T.fact_examples + T.render_conversation (LoCoMo)", extract_session),
                     ("T.build_tagging_memory_prompt (SynthPAI D.4)", annotate),
                     ("T.SESSION_CHECK_PROMPT (added)", check_session), ("T.CROSS_SESSION_PROMPT (added)", cross_check),
                     ("T.SPLIT_PROMPT (added)", split_item)):
        sites.append(f"| {tmpl} | scripts/v2_dialogue_preview.py::{fn.__name__} | {inspect.getsourcelines(fn)[1]} |")
    open(os.path.join(tdir, "CALL_SITES.md"), "w").write("\n".join(sites) + "\n")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


# ------------------------------------------------------------------------------------------------------ main

def main():
    global POOL
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "data_v2_dialogue_preview"))
    ap.add_argument("--input", default=os.path.join(ROOT, "data_v2_preview", "pf", "us_households.jsonl"))
    ap.add_argument("--prev_manifest", default=os.path.join(ROOT, "data_v2_preview", "manifest.json"))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default="qwen3:32b")
    ap.add_argument("--servers", default="http://localhost:11434=1")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--num_ctx", type=int, default=8192)
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()
    POOL = ServerPool(args.servers)
    os.makedirs(args.out, exist_ok=True)
    write_provenance(args.out)

    people = [json.loads(l) for l in open(args.input)]
    by_id = {p["profile_id"]: p for p in people}
    households = defaultdict(list)
    for p in people:
        households[p["household_id"]].append(p["profile_id"])

    # selection: u001-u006 keep their ProfileFoundry ids; two partnered adults aged 28-45 get synthetic minor children
    chosen = [by_id[s["profile_id"]] for s in json.load(open(args.prev_manifest))["personas"]]
    sel_rng = random.Random(f"{args.seed}-select")
    used = {p["household_id"] for p in chosen}
    cands = sorted((p for p in people if 28 <= age_on(p["identity"]["dob"]) <= 45 and p["family"].get("spouse") in by_id
                    and by_id[p["family"]["spouse"]]["household_id"] == p["household_id"] and not p["family"].get("children")
                    and p["household_id"] not in used), key=lambda p: p["profile_id"])
    sel_rng.shuffle(cands)
    extra, seen = [], set()
    for p in cands:
        if p["household_id"] not in seen:
            extra.append(p)
            seen.add(p["household_id"])
        if len(extra) == 2:
            break
    syn_kids = {}
    for p in extra:
        sp = by_id[p["family"]["spouse"]]
        youngest_parent = min(age_on(p["identity"]["dob"]), age_on(sp["identity"]["dob"]))
        n = sel_rng.choice([1, 2])
        ages = sorted((sel_rng.randint(0, min(17, youngest_parent - 20)) for _ in range(n)), reverse=True)
        syn_kids[p["profile_id"]] = [{"child_id": f"syn_child_{p['profile_id'][-4:]}_{i + 1}", "age": a, "sex": sel_rng.choice(["girl", "boy"]),
                                      "parents": [p["profile_id"], sp["profile_id"]], "lives_with_persona": True,
                                      "source": "synthetic", "basis": "rule-added for this preview: 1-2 children, age uniform in "
                                      "[0, min(17, younger parent's age - 20)]"} for i, a in enumerate(ages)]

    profiles = []
    for i, p in enumerate(chosen + extra):
        pid = f"u{i + 1:03d}"
        profiles.append(build_profile(pid, p, by_id, households, syn_kids.get(p["profile_id"], []), random.Random(f"{args.seed}-profile-{pid}")))
    examples = T.fact_examples(json.load(open(os.path.join(ROOT, "external", "upstream_templates", "locomo", "fact_generation_examples_new.json"))))

    def run_persona(pr):
        pid = pr["persona_id"]
        hist = build_history(args, pr, random.Random(f"{args.seed}-history-{pid}"))      # no access to tasks
        mem = build_memory(args, pr, hist, examples) if hist["kept"] else {"raw": [], "filtered": {"age_cue_only": {"memory": [], "removed": []}}, "age_cue_only_regex_flags": []}
        tasks = build_tasks(args, pr, random.Random(f"{args.seed}-tasks-{pid}"))        # separate RNG stream
        for d, obj in (("personas", pr), ("history", hist), ("tasks", tasks)):
            os.makedirs(os.path.join(args.out, d), exist_ok=True)
            json.dump(obj, open(os.path.join(args.out, d, f"{pid}.json"), "w"), indent=2, ensure_ascii=False)
        os.makedirs(os.path.join(args.out, "memory", "raw"), exist_ok=True)
        json.dump({"persona_id": pid, "memory": mem["raw"]}, open(os.path.join(args.out, "memory", "raw", f"{pid}.json"), "w"), indent=2, ensure_ascii=False)
        for name, v in mem["filtered"].items():
            os.makedirs(os.path.join(args.out, "memory", "filtered", name), exist_ok=True)
            json.dump({"persona_id": pid, **v}, open(os.path.join(args.out, "memory", "filtered", name, f"{pid}.json"), "w"), indent=2, ensure_ascii=False)
        os.makedirs(os.path.join(args.out, "view"), exist_ok=True)
        open(os.path.join(args.out, "view", f"{pid}.md"), "w").write(view(pr, hist, mem, tasks))
        print(f"{pid}: history {hist['status']} ({len(hist['kept'])} kept, {len(hist['dropped'])} dropped); "
              f"memory {len(mem['raw'])} items; age_cue_only {len(mem['filtered']['age_cue_only']['memory'])}", flush=True)
        return pr, hist, mem, tasks

    with cf.ThreadPoolExecutor(len(profiles)) as ex:
        results = list(ex.map(run_persona, profiles))

    json.dump(dict(LOG), open(os.path.join(args.out, "failures_and_repairs.json"), "w"), indent=2, ensure_ascii=False)
    digest = None
    try:
        with urllib.request.urlopen(POOL.servers[0][0] + "/api/tags", timeout=30) as r:
            digest = next((m["digest"] for m in json.loads(r.read())["models"] if m["name"] == args.model), None)
    except Exception:
        pass
    json.dump({"seed": args.seed, "model": args.model, "model_digest": digest, "reference_date": REFERENCE.isoformat(),
               "history_window": [d.isoformat() for d in WINDOW], "input": os.path.relpath(args.input, ROOT),
               "input_sha256": sha(args.input), "code_sha256": {f: sha(os.path.join(HERE, f)) for f in ("v2_dialogue_preview.py", "v2_templates.py")},
               "upstream": json.load(open(os.path.join(ROOT, "external", "upstream_templates", "SOURCES.json"))),
               "profilefoundry": "GitHub generator commit 8239180 (Citation License 1.0); gated HF dataset not used",
               "personas": [{"persona_id": pr["persona_id"], "profile_id": pr["source"]["profile_id"]} for pr, *_ in results],
               "llm_calls": STATS["llm_calls"], "args": {k: v for k, v in vars(args).items() if k != "servers"}},
              open(os.path.join(args.out, "manifest.json"), "w"), indent=2)
    json.dump([{"persona_id": pr["persona_id"], "history_status": h["status"], "kept": len(h["kept"]), "dropped": len(h["dropped"]),
                "raw_memory": len(m["raw"]), "age_cue_only": len(m["filtered"]["age_cue_only"]["memory"])} for pr, h, m, t in results],
              open(os.path.join(args.out, "run_summary.json"), "w"), indent=2)
    print("done; LLM calls:", STATS["llm_calls"])


if __name__ == "__main__":
    main()
