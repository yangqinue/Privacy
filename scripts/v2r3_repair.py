"""Repair version r3 of the dataset v2 dialogue preview. r2 (data_v2_dialogue_preview_r2/) is read only.

Nothing is regenerated wholesale. Stages:
  regression  run the r3 session checks on hand-verified cases (must pass before the checks are used on data)
  recheck     re-check every r2 session attempt (kept and dropped) with the r3 checks; audit user statements
  repair      restore wrongly dropped sessions, regenerate only sessions with a real problem, rewrite profile-reciting
              user messages; no session is generated just to reach 12
  memory      re-extract memory and build the chain  source -> user statement -> memory entry -> attribute label
  write       personas/catalogs/tasks (copied, statuses recomputed), view pages, REPAIRS.md, numbers.json

Usage:
  python scripts/v2r3_repair.py --stage regression|all --servers http://localhost:11436=4,...
"""

import argparse
import concurrent.futures as cf
import copy
import datetime as dt
import glob
import hashlib
import json
import os
import random
import re
import shutil
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import v2r2_dialogue_preview as R
import v2r2_templates as T2
import v2r3_templates as T
from run_dev2 import ServerPool

P1 = R.P1
ATTRS = R.ATTRS
MONTHS, WEEKDAYS = R.MONTHS, R.WEEKDAYS
norm, as_json, cseed, dtext = R.norm, R.as_json, R.cseed, R.dtext
ARGS = None
REPAIRS = []            # the repair list (one record per change)

COMPLETION_RE = (r"\b(I(?:'ve| have)(?: just| now| already)? (?:booked|reserved|placed|ordered|purchased|changed|updated|rescheduled|confirmed|scheduled)"
                 r"|(?:has|have) been (?:booked|reserved|placed|ordered|confirmed|changed|updated|rescheduled|scheduled)"
                 r"|(?:is|are) (?:now )?(?:booked|confirmed|reserved)\b"
                 r"|(?:order|reservation|booking|delivery)\b[^.?!]{0,80}\bis (?:all )?set\b"
                 r"|confirmation (?:number|code)(?: is|:)?\s*#?[A-Z]*-?\d)")
BRAND_RE = (r"\b(Verizon|AT&T|T-Mobile|Mint Mobile|Google Fi|Sprint|Cricket Wireless|Xfinity Mobile|US Cellular|Instacart|Amazon Fresh|"
            r"Whole Foods|Walmart|OpenTable|Ticketmaster|StubHub|Airbnb|Yelp|Expedia|Booking\.com)\b")
CONTACT_RE = r"\(\d{3}\)\s?\d{3}-\d{4}|\b\d{3}-\d{3}-\d{4}\b|https?://|\bwww\.\w"


_REL = r"my (?:son|daughter|wife|husband|partner|kids?|child(?:ren)?|mom|mother|dad|father|parents|brother|sister|friend)"
_DIET = r"(?:low-sodium|gluten|vegetarian|vegan|lactose|dairy|allerg\w+|diabet\w+|shellfish|nut-free|dietary (?:need|restriction)s?)"
RELATIVE_HEALTH_RE = rf"{_DIET}[^.?!]{{0,40}}\b(?:for|because of) {_REL}\b|\b{_REL} (?:is|has|can't|cannot|needs?|doesn't|does not)[^.?!]{{0,40}}{_DIET}"
INTENT_RE = (r"\b(I'll|I will|I can|I could|let me|I'm going to|I am going to|would you|do you|could you|can you|should I|shall I|"
             r"ensure|make sure|once|if |when |whether|want me to|like me to)\b")


def sentence_before(text, pos):
    """The part of the sentence that precedes position pos."""
    start = max(text.rfind(x, 0, pos) for x in (". ", "! ", "? ", "\n")) + 1
    return text[max(0, start):pos]


def rep(kind, **kw):
    with P1.LOCK:
        REPAIRS.append({"kind": kind, **kw})


def raw_ask(args, messages, seed, pid, tag, think, json_mode, temperature):
    """Like P1.ask but with an output cap: at temperature 0 the model sometimes reasons without end (15-minute calls
    in the first r3 pass). A capped reply that cannot be parsed is retried by the caller with another seed."""
    import urllib.request
    d = os.path.join(args.out, "templates", "rendered", pid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{tag}.txt"), "w") as f:
        for m in messages:
            f.write(f"--- {m['role']} ---\n{m['content']}\n")
    body = {"model": args.model, "stream": False, "think": think, "messages": messages,
            "options": {"temperature": args.temperature if temperature is None else temperature, "seed": seed, "num_ctx": args.num_ctx,
                        "num_predict": 3500 if think else 900}}
    if json_mode and not think:
        body["format"] = "json"
    last = None
    for attempt in range(2):
        srv = P1.POOL.acquire()
        try:
            req = urllib.request.Request(srv[0] + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=420) as r:
                msg = json.loads(r.read())["message"]
            with P1.LOCK:
                P1.STATS["llm_calls"] += 1
            return msg.get("content", ""), msg.get("thinking")
        except Exception as e:
            last = e
        finally:
            P1.POOL.release(srv)
    raise RuntimeError(f"LLM call failed: {last}")


def ask(args, messages, seed, pid, tag, think=False, json_mode=False, temperature=None):
    """P1.ask with an on-disk cache keyed by the full request, so stages can be re-run without new calls."""
    key = hashlib.sha1(json.dumps([messages, think, json_mode, temperature, seed, args.model], sort_keys=True).encode()).hexdigest()
    path = os.path.join(args.out, "cache", key[:2], key + ".json")
    if os.path.exists(path):
        c = json.load(open(path))
        return c["content"], c.get("thinking")
    content, thinking = raw_ask(args, messages, seed, pid, tag, think, json_mode, temperature)
    if not content.strip():
        raise RuntimeError("empty reply (output cap reached while reasoning)")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump({"content": content, "thinking": thinking, "tag": f"{pid}/{tag}"}, open(path, "w"))
    return content, thinking


R.ask = ask           # r2 functions reused below (extraction, grouping, annotation) go through the cache too


# ------------------------------------------------------------------------------------------------ dates (code)

def date_mentions(text, d0):
    """Explicit day+month mentions in a text -> [(raw, date)], the year chosen closest to the session date."""
    mo = "|".join(f"{x[:3]}(?:{x[3:]})?" if len(x) > 3 else x for x in MONTHS)
    out = []
    pats = [(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?(?: of)? ({mo})\b(?!\w)", lambda m: (int(m.group(1)), m.group(2))),
            (rf"\b({mo})\.? (\d{{1,2}})(?:st|nd|rd|th)?\b(?!:|\s?(?:GB|pm|am|people|lines))", lambda m: (int(m.group(2)), m.group(1)))]
    for pat, get in pats:
        for m in re.finditer(pat, text):
            day, month = get(m)
            for y in (d0.year - 1, d0.year, d0.year + 1):
                try:
                    c = dt.date(y, [x[:3] for x in MONTHS].index(month[:3]) + 1, day)
                except ValueError:
                    continue
                if -60 <= (c - d0).days <= 305:
                    out.append((m.group(0), c))
                    break
    return out


def allowed_dates(ctx, d0):
    """Dates a session may mention: those written in the situation (with the rest of that weekend or week), today, tomorrow."""
    al = set()                    # r3: today/tomorrow are not allowed by default (they hid three wrong dates)
    for e in ctx["elements"].values():
        for raw, c in date_mentions(e["text"], d0):
            al.add(c)
        if "week starting" in e["text"]:
            for raw, c in date_mentions(e["text"], d0):
                al.update(c + dt.timedelta(days=i) for i in range(7))
    al.update(dt.date.fromisoformat(x) for x in ctx.get("extra_dates", []))
    for c in list(al):
        if c != d0 and c.strftime("%A") in ("Friday", "Saturday", "Sunday"):
            fri = c - dt.timedelta(days=("Friday", "Saturday", "Sunday").index(c.strftime("%A")))
            al.update(fri + dt.timedelta(days=i) for i in range(3))
    return al or {d0}


def amend_fitness(ctx, d0, single):
    """r3: fitness situations get calendar dates for the days named (code). For existing r2 conversations both of the
    next two occurrences are registered; for regenerated conversations exactly one date per day is given."""
    el = ctx["elements"].get("ctx.days")
    if not el or "(" in el["text"]:
        return ctx
    days = [w for w in WEEKDAYS if re.search(rf"\b{w}\b", el["text"])]
    days.sort(key=lambda w: el["text"].index(w))
    week = None
    if "ctx.when" in ctx["elements"]:
        wk = date_mentions(ctx["elements"]["ctx.when"]["text"], d0)
        week = wk[0][1] if wk else None
    parts, extra = [], []
    for w in days:
        if week:
            occ = [week + dt.timedelta(days=WEEKDAYS.index(w))]
        else:
            first = next(d0 + dt.timedelta(days=i) for i in range(1 if single else 0, 9) if (d0 + dt.timedelta(days=i)).strftime("%A") == w)
            occ = [first] if single else [first, first + dt.timedelta(days=7)]
        extra += occ
        parts.append(dtext(occ[0]) if len(occ) == 1 else f"{w} ({' or '.join(str(o.day) + ' ' + MONTHS[o.month - 1] for o in occ)} {occ[-1].year})")
    el["text"] = "days that suit you this time: " + " and ".join(parts)
    ctx["extra_dates"] = sorted({x.isoformat() for x in extra})
    ctx["text"] = "\n        ".join("- " + e["text"] for e in ctx["elements"].values())
    ctx["r3_amended"] = "fitness dates added by code"
    return ctx


# ----------------------------------------------------------------------------------------------- source elements

def detailed_elements(pr, d, ctx):
    """Registered sources with their values, as shown to the statement audit; links follow the r3 rule:
    only our own child rule (minor children) counts as generated together with age; ProfileFoundry links stay unverified."""
    f = {k: v["value"] for k, v in pr["fields"].items()}
    iso = d.isoformat()
    base = R.profile_elements(pr)
    later = [e for e in f["life_events"] if e["date"] > iso]
    marital_open = any(e["type"] in ("marriage", "divorce") for e in later)
    partner, kids, rel, n_home = R.household(pr)
    spouse_name = next((e["text"].replace("married ", "") for e in reversed(f["life_events"]) if e["type"] == "marriage" and e["date"] <= iso), None)
    text = {
        "profile.age": f"age {P1.age_on(f['date_of_birth'], d)} on this date; given name {f['given_name']}; gender {f['gender']}",
        "profile.marital_partner": ("not shown for this date" if marital_open else f"marital status {f['marital_status']}; "
                                    + (f"{partner} lives in the same home" + (f" (name: {spouse_name})" if spouse_name else "") if partner else "no partner at home")),
        "profile.minor_children": ", ".join(k[0] for k in kids) or "none recorded",
        "profile.adult_children": ", ".join(f"{R.rel_label({'relation': 'adult child', 'gender': a.get('gender')}) if a.get('gender') else 'adult child'} aged {a['age']}"
                                            for a in f["co_resident_adults"] if a["relation"] == "adult child") or "none at home",
        "profile.co_residents": ", ".join(f"{r[0]} (age {r[2]})" for r in rel if r[1] != "adult child") or "none"
                                + f"; {n_home} people live in the home in total",
        "profile.job": (f"{f['employment']['job_title']} at {f['employment']['employer']}; working hours not recorded"
                        if f["employment"]["status"] == "Employed" else "unknown"),
        "profile.education": f"{f['education']['degree']} ({f['education']['institution']})" if isinstance(f["education"], dict) else "unknown",
        "profile.city": f"lives in {f['city']}",
        "profile.health": "allergies: " + (", ".join(f["health"]["allergies"]) or "none recorded")
                          + (f"; disability: {f['health']['disability']}" if f["health"]["disability"] else ""),
        "profile.life_events": "; ".join(f"{e['date'][:7]} {e['text']}" for e in f["life_events"] if e["date"] <= iso) or "none",
    }
    E = {}
    for k, v in base.items():
        link = dict(v["link"])
        if k in ("profile.adult_children", "profile.life_events") and link["age"] == "co_generated":
            link["age"] = "unverified"
        E[k] = {"text": text.get(k, v["text"]), "source": v["source"], "link": link}
    for k, v in (ctx["elements"] if ctx else {}).items():
        link = dict(v["link"])
        if link["age"] == "co_generated" and not (kids and ("year-old" in v["text"] or k == "ctx.household")):
            link["age"] = "unverified"
        E[k] = {"text": v["text"], "source": v["source"], "link": link}
    return E


# ------------------------------------------------------------------------------------------------ session check

STATES = {"WV": "West Virginia", "TX": "Texas", "PA": "Pennsylvania", "NY": "New York", "SD": "South Dakota", "TN": "Tennessee", "IL": "Illinois"}
NAME_STOP = set(("I I'll I'm I've I'd Let Sure Great Thanks Thank Yes No Got Do Would Could Can Here Please Also If For To And Or But The A An It "
                 "That This These Those You Your We Our My OK Okay Understood Of Once When While Since Just Hi Hey Hello Noted Absolutely Perfect "
                 "Good Some Many Most Any All What Which How Are Is Be Will Should May Might Fri Sat Sun Mon Tue Wed Thu AM PM GB R&B K-pop EDM "
                 "Christmas Thanksgiving Eve New Year's Day").split()) | set(MONTHS) | set(WEEKDAYS) | {m[:3] for m in MONTHS} | {"Sept"}
HELPER_VOICE_RE = (r"\b(do you have any (dietary|specific|preferred|other)|would you like me to|should I (mention|add|note|check|look)|"
                   r"is there anything (else )?you('d| would) like|let me (check|look|find|search)|I'll (look|check|search|find) (for|into|if)|how (can|may) I help)\b")


def new_names(text, allowed_words):
    """Capitalised names in an assistant message that appear nowhere in the user's words, the situation, the city or
    the persona's local catalog (e.g. a real park or town the assistant brings up on its own)."""
    out = []
    for m in re.finditer(r"\b([A-Z][a-z]+(?:[ -](?:[A-Z][a-z]+|&|of|the))*)", text):
        before = text[:m.start()].rstrip()
        if not before or before[-1] in ".!?:\n-*":
            continue
        toks = [t for t in re.split(r"[ -]", m.group(1)) if t[:1].isupper()]
        if not all(t in NAME_STOP or t.lower() in allowed_words for t in toks):
            out.append(m.group(1))
    return out


def code_problems(s, d0, allowed, pr=None, cat=None):
    probs = R.date_problems(s["turns"], d0)
    if pr is not None:
        city = pr["fields"]["city"]["value"]
        base = " ".join(t["text"] for t in s["turns"] if t["speaker"] == "User") + " " + (s.get("context") or {}).get("text", "") + " " + city + " " \
            + STATES.get(city.split(", ")[-1], "") + " " + json.dumps(cat or {})
        aw = {w.lower() for w in re.findall(r"[A-Za-z][a-z]+", base)}
        gn = pr["fields"]["given_name"]["value"]
        for t in s["turns"]:
            if t["speaker"] == "Assistant":
                nn = new_names(t["text"], aw)
                if nn:
                    probs.append({"type": "assistant_invented_listing", "quote": nn[0], "source": "code",
                                  "reason": f"assistant brings up names nobody mentioned ({t['dia_id']}): {', '.join(nn[:4])}"})
            else:
                m = re.search(HELPER_VOICE_RE, t["text"], re.I)
                if m:
                    probs.append({"type": "role_swap", "quote": m.group(0), "source": "code", "reason": f"user message {t['dia_id']} is written in the helper's voice"})
                m = re.search(r"\bI work\b|\bmy (?:shift|work hours|working hours)\b|\b(?:after|before) work\b|\b(?:we both|both of us) (?:have|are)\b", t["text"], re.I)
                if m:                    # working hours are never in the profile; facts about a companion are never registered
                    probs.append({"type": "new_identity_fact", "quote": m.group(0), "source": "code", "reason": f"user message {t['dia_id']} states a work schedule or a fact about a companion"})
                if re.search(rf"\b{re.escape(gn)}\b", t["text"]):
                    probs.append({"type": "role_swap", "quote": gn, "source": "code", "reason": f"user message {t['dia_id']} speaks of the user by name, in the third person"})
    said = ""
    for i, t in enumerate(s["turns"]):
        if allowed is not None:
            for raw, c in date_mentions(t["text"], d0):
                if c not in allowed:
                    probs.append({"type": "date_not_registered", "quote": raw, "source": "code",
                                  "reason": f"{t['speaker']} mentions {c.isoformat()} in {t['dia_id']}; the situation registers "
                                            + ", ".join(sorted(x.isoformat() for x in allowed if x != d0)[:6])})
        if t["speaker"] == "Assistant":
            for pat, typ in ((COMPLETION_RE, "assistant_claims_completion"), (CONTACT_RE, "assistant_invented_listing")):
                m = re.search(pat, t["text"], re.I)
                if m and typ == "assistant_claims_completion" and re.search(INTENT_RE, sentence_before(t["text"], m.start()), re.I):
                    m = None        # "I'll make sure the delivery is set for Tuesday" is an intention, not a completed action
                if m:
                    probs.append({"type": typ, "quote": m.group(0), "source": "code", "reason": f"assistant has no tools ({t['dia_id']})"})
            for m in re.finditer(BRAND_RE, t["text"]):
                if m.group(0).lower() not in said.lower():
                    probs.append({"type": "assistant_invented_listing", "quote": m.group(0), "source": "code",
                                  "reason": f"assistant names a real company the user did not name ({t['dia_id']})"})
                    break
        else:
            m = re.search(RELATIVE_HEALTH_RE, t["text"], re.I)
            if m:                        # a diet or health need attributed to a relative is never registered in this data
                probs.append({"type": "new_identity_fact", "quote": m.group(0), "source": "code",
                              "reason": f"diet or health need attributed to a relative ({t['dia_id']}); profiles record these for the user only"})
            w = set(re.findall(r"[a-z0-9']+", t["text"].lower()))
            for p in s["turns"][:i]:
                pw = set(re.findall(r"[a-z0-9']+", p["text"].lower()))
                if p["speaker"] == "Assistant" and len(w) > 6 and len(w & pw) / max(1, len(w | pw)) >= 0.8:
                    probs.append({"type": "role_swap", "quote": t["text"][:80], "source": "code",
                                  "reason": f"user message {t['dia_id']} repeats the assistant's message {p['dia_id']}"})
            said += " " + t["text"]
    return probs


def llm_assistant_check(pid, s, pub_text, tag):
    d0 = dt.date.fromisoformat(s["date"])
    conv = "\n".join(f"[{t['dia_id']}] {t['speaker']}: {t['text']}" for t in s["turns"])
    prompt = T.ASSISTANT_CHECK_PROMPT.format(public_context=pub_text, date=dtext(d0), conversation=conv)
    text, _ = ask(ARGS, [{"role": "user", "content": prompt}], cseed(ARGS, pid, "acheck", tag), pid, f"acheck_{tag}", think=True, temperature=0.0)
    out, rejected = [], 0
    types = ("assistant_knew_in_advance", "assistant_claims_completion", "assistant_invented_listing", "role_swap")
    for p in as_json(text).get("problems", []):
        if not (isinstance(p, dict) and p.get("type") in types):
            continue
        q = norm(p.get("quote", ""))
        ok = len(q) >= 5 and any(q in norm(t["text"]) for t in s["turns"] if p["type"] == "role_swap" or t["speaker"] == "Assistant")
        if ok and p["type"] == "assistant_claims_completion" and not re.search(
                r"\b(i've|i have|has been|have been|successfully|all set|is (now )?(booked|confirmed|reserved|placed|scheduled|set up))\b", q):
            ok = False                   # "I'm checking now", "adding X is a great choice" are not completed actions
        if ok and p["type"] in ("assistant_claims_completion", "assistant_invented_listing"):
            # the quoted words must not be a statement of intent or a question ("I'll check ... on Fri 12 Dec")
            for t in s["turns"]:
                i = norm(t["text"]).find(q)
                if t["speaker"] == "Assistant" and i >= 0 and re.search(INTENT_RE, sentence_before(norm(t["text"]), i) + " " + q[:40], re.I):
                    ok = False
        if ok:
            out.append({**p, "source": "llm"})
        else:
            rejected += 1
    return out, rejected


def audit_claims(pid, s, elements, tag):
    """Every user statement -> registered / unregistered_detail / new_identity_fact / contradiction, with source ids."""
    d0 = dt.date.fromisoformat(s["date"])
    msgs = "\n".join(f"[{t['dia_id']}] {t['text']}" for t in s["turns"] if t["speaker"] == "User")
    el = "\n".join(f"- {k}: {v['text']}" for k, v in elements.items())
    prompt = T.CLAIMS_PROMPT.format(elements=el, date=dtext(d0), messages=msgs)
    text, _ = ask(ARGS, [{"role": "user", "content": prompt}], cseed(ARGS, pid, "claims", tag), pid, f"claims_{tag}", think=True, temperature=0.0)
    by = {t["dia_id"]: t for t in s["turns"] if t["speaker"] == "User"}
    claims, rejected = [], 0
    for c in as_json(text).get("claims", []):
        if not isinstance(c, dict) or c.get("kind") not in ("registered", "unregistered_detail", "new_identity_fact", "contradiction"):
            continue
        t = by.get(c.get("id"))
        if not t or len(norm(c.get("quote", ""))) < 3 or norm(c["quote"]) not in norm(t["text"]):
            rejected += 1
            continue
        els = [e for e in c.get("elements", []) if e in elements] if c["kind"] == "registered" else []
        kind = c["kind"] if not (c["kind"] == "registered" and not els) else "unregistered_detail"   # 'registered' needs a source id
        if kind == "unregistered_detail" and re.search(r"new[ _]identity", str(c.get("reason", "")), re.I):
            kind = "new_identity_fact"   # the model's own reason names it but the label was softened
        if kind == "contradiction":      # a second, narrow call must confirm a real conflict
            try:
                out, _ = ask(ARGS, [{"role": "user", "content": T.CONTRADICTION_CONFIRM_PROMPT.format(elements=el, dia_id=c["id"], quote=c["quote"], reason=c.get("reason", ""))}],
                             cseed(ARGS, pid, "confirm", tag, c["quote"]), pid, f"confirm_{tag}_{len(claims) + 1}", json_mode=True, temperature=0.0)
                if str(as_json(out).get("conflict", "")).lower() != "yes":
                    kind = "unregistered_detail"
                    c["reason"] = "flagged as contradiction, not confirmed: " + str(c.get("reason", ""))
            except Exception:
                pass
        claims.append({"cid": f"c{len(claims) + 1}", "dia_id": c["id"], "quote": c["quote"], "kind": kind, "elements": els,
                       "reason": str(c.get("reason", ""))[:200]})
    return claims, rejected


def check_v3(pr, s, pub_text, ctx, tag, use_dates=True):
    pid = pr["persona_id"]
    d0 = dt.date.fromisoformat(s["date"])
    elements = detailed_elements(pr, d0, ctx)
    cat_path = os.path.join(ARGS.r2, "catalogs", f"{pid}.json")
    probs = code_problems(s, d0, allowed_dates(ctx, d0) if (ctx and use_dates) else None, pr, json.load(open(cat_path)) if os.path.exists(cat_path) else None)
    err = None
    for k in range(3):                 # a failed or unparsable model reply is retried, never counted as a problem
        try:
            lp, rej_a = llm_assistant_check(pid, s, pub_text, tag if k == 0 else f"{tag}_retry{k}")
            claims, rej_c = audit_claims(pid, s, elements, tag if k == 0 else f"{tag}_retry{k}")
            err = None
            break
        except Exception as e:
            err = str(e)
    if err:
        return {"status": "check_failed", "problems": probs, "claims": [], "error": err}
    seen = {(p["type"]) for p in probs if p["source"] == "code"}
    probs += [p for p in lp if not (p["type"] in seen and p["type"] in ("assistant_claims_completion", "role_swap"))]
    for c in claims:
        if c["kind"] in ("new_identity_fact", "contradiction"):
            probs.append({"type": c["kind"], "quote": c["quote"], "source": "llm-audit", "reason": f"{c['dia_id']}: {c['reason']}"})
    return {"status": "ok" if not probs else "not_ok", "problems": probs, "claims": claims,
            "rejected_llm_findings": {"assistant_check_quote_not_found": rej_a, "claim_quote_not_found": rej_c}}


# --------------------------------------------------------------------------------------------------- regression

def regression(profiles):
    """Hand-verified cases. expect_ok: the checks must find nothing. must_raise / must_not_raise: problem types."""
    cases = json.load(open(os.path.join(HERE, "v2r3_regression_cases.json")))
    r1 = {(x["persona_id"], x["session_id"]): x for x in json.load(open(os.path.join(ARGS.r2, "comparison", "old_dropped_recheck.json")))}
    H2 = {p: json.load(open(os.path.join(ARGS.r2, "history", f"{p}.json"))) for p in profiles}

    def run(c):
        pr = profiles[c["persona"]]
        if c["source"] == "r1":
            s = r1[(c["persona"], c["session"])]
            res = check_v3(pr, s, "- Nothing (in revision 1 the assistant was given no context).", None, f"reg_r1_{c['session']}")
        else:
            s = next(x for x in H2[c["persona"]]["kept"] + H2[c["persona"]]["dropped"]
                     if x["session_id"] == c["session"] and x.get("regenerated", 0) == c.get("attempt", 0))
            d0 = dt.date.fromisoformat(s["date"])
            ctx = amend_fitness(copy.deepcopy(s["context"]), d0, single=False)
            res = check_v3(pr, s, R.public_context(pr, d0, R.persona_at(pr, d0)[1])["text"], ctx, f"reg_r2_{c['session']}_{c.get('attempt', 0)}")
        got = {p["type"] for p in res["problems"]}
        ok = res["status"] != "check_failed"
        if c.get("expect_ok"):
            ok = ok and not got
        ok = ok and not (set(c.get("must_not_raise", [])) & got) and set(c.get("must_raise", [])) <= got
        return {**c, "passed": ok, "raised": sorted(got), "problems": [{k: p[k] for k in ("type", "source", "quote", "reason")} for p in res["problems"]]}

    with cf.ThreadPoolExecutor(8) as ex:
        results = list(ex.map(run, cases))
    json.dump(results, open(os.path.join(ARGS.out, "regression_results.json"), "w"), indent=2, ensure_ascii=False)
    bad = [r for r in results if not r["passed"]]
    print(f"regression: {len(results) - len(bad)}/{len(results)} passed")
    for r in bad:
        print("  FAIL", r["source"], r["persona"], r["session"], r.get("attempt", 0), "| expected:", {k: r[k] for k in ("expect_ok", "must_raise", "must_not_raise") if k in r},
              "| raised:", [(p["type"], p["source"], p["quote"][:70]) for p in r["problems"]])
    return results


# ---------------------------------------------------------------------------------------------- recheck + repair

def simulate_r3(pr, s, ctx, pub, persona, attempt):
    """Same prompts as r2; the user simulator now sees one transcript instead of role-flipped messages."""
    pid, sid = pr["persona_id"], s["session_id"]
    sys_u = T2.user_simulator_prompt(persona, P1.preference_text(pr, s["activity"]), ctx["text"], s["date_text"], s["errand"])
    sys_a = T2.HISTORY_ASSISTANT_PROMPT.format(public_context=pub["text"])
    n_user = 2 + cseed(ARGS, pid, "turns", sid, attempt) % 2
    conv = []
    for i in range(n_user):
        for speaker in ("user", "assistant"):
            msgs = ([{"role": "system", "content": sys_u}, {"role": "user", "content": T.user_turn_request(conv, i == n_user - 1 and i > 0)}]
                    if speaker == "user" else [{"role": "system", "content": sys_a}] + [{"role": t["role"], "content": t["content"]} for t in conv])
            text = ""
            for r in range(3):
                out, _ = ask(ARGS, msgs, cseed(ARGS, pid, "sim3", sid, attempt, len(conv), r), pid, f"sim_{sid}_r3a{attempt}_{len(conv) + 1}_{speaker}")
                text = R.clean(out)
                if text:
                    break
            if not text:
                return None
            conv.append({"role": speaker, "content": text})
    n = int(sid[1:])
    turns = [{"dia_id": f"D{n}:{i + 1}", "speaker": "User" if t["role"] == "user" else "Assistant", "text": t["content"]} for i, t in enumerate(conv)]
    return {**{k: s[k] for k in ("session_id", "date", "date_text", "activity", "errand")}, "context": ctx,
            "assistant_public_context": {k: pub[k] for k in ("provided", "not_provided")}, "turns": turns, "regenerated": attempt, "generated_in": "r3"}


def recite_tokens(pr, text):
    """Family details a user message recites beyond what an errand needs: ages of adults, several ages, relatives' names."""
    f = {k: v["value"] for k, v in pr["fields"].items()}
    ages = [int(x) for x in re.findall(r"\b(\d{1,2})[- ]year[- ]old", text)]
    m = re.search(r"\b(?:ages?|aged)\b[^.?!]{0,12}?((?:\d{1,2}(?:, | and |, and )?)+)", text)
    if m:
        ages += [int(x) for x in re.findall(r"\d{1,2}", m.group(1))]
    names = [e["text"].replace("married ", "").split()[0] for e in f["life_events"] if e["type"] == "marriage"]
    named = [n for n in names if re.search(rf"\b{re.escape(n)}\b", text)]
    if len(ages) >= 2 or any(a >= 18 for a in ages) or (named and ages):
        return {"ages": ages, "names": named}
    return None


def rewrite_recital(pr, s):
    """Rewrite user messages that recite family details; later messages echoing the removed details are rewritten too."""
    pid = pr["persona_id"]
    changed, removed = [], {"ages": set(), "names": set()}
    for t in s["turns"]:
        tok = recite_tokens(pr, t["text"]) if t["speaker"] == "User" else None
        echo = (t["speaker"] == "Assistant" and (any(re.search(rf"\b{re.escape(n)}\b", t["text"]) for n in removed["names"])
                                                  or (removed["ages"] and re.search(r"\b(ages?|aged)\b|\d{1,2}[- ]year[- ]old", t["text"]))))
        if not tok and not echo:
            continue
        try:
            out, _ = ask(ARGS, [{"role": "user", "content": T.REWRITE_PROMPT.format(errand=s["errand"], text=t["text"])}],
                         cseed(ARGS, pid, "rewrite", t["dia_id"]), pid, f"rewrite_{t['dia_id'].replace(':', '_')}", json_mode=True, temperature=0.0)
            new = str(as_json(out).get("text", "")).strip()
        except Exception:
            new = ""
        if not new or new == t["text"]:
            continue
        if tok:
            left = recite_tokens(pr, new) or {"ages": [], "names": []}
            removed["ages"] |= set(tok["ages"]) - set(left["ages"])
            removed["names"] |= set(tok["names"]) - set(left["names"])
        changed.append({"dia_id": t["dia_id"], "speaker": t["speaker"], "before": t["text"], "after": new})
        t["text"] = new
    if changed:
        s["rewritten_in_r3"] = changed
        rep("user_message_rewritten", persona=pid, session=s["session_id"], changes=changed,
            why="recited family details beyond what the errand needs (ages of adults, several ages, or a relative's name with an age)")
    return bool(changed)


def repair_history(pr, cat, standing, H2):
    pid = pr["persona_id"]
    attempts = defaultdict(list)
    for s in H2["kept"] + H2["dropped"]:
        if s.get("turns"):
            attempts[s["session_id"]].append({**copy.deepcopy(s), "r2_status": "kept" if s in H2["kept"] else "dropped"})

    def pub_of(s):
        d0 = dt.date.fromisoformat(s["date"])
        return R.public_context(pr, d0, R.persona_at(pr, d0)[1])

    def recheck(s):
        d0 = dt.date.fromisoformat(s["date"])
        amend_fitness(s["context"], d0, single=False)
        s["check_r2"] = s.pop("check")
        s["check"] = check_v3(pr, s, pub_of(s)["text"], s["context"], f"{s['session_id']}_a{s.get('regenerated', 0)}")
        return s

    with cf.ThreadPoolExecutor(4) as ex:
        allatt = list(ex.map(recheck, [a for v in attempts.values() for a in v]))
    kept, dropped, todo = [], [], []
    for sid in sorted(attempts):
        att = sorted(attempts[sid], key=lambda a: a.get("regenerated", 0))
        good = [a for a in att if a["check"]["status"] == "ok"]
        if good:
            g = good[0]
            kept.append(g)
            if g["r2_status"] == "dropped":
                rep("session_restored", persona=pid, session=sid, attempt=g.get("regenerated", 0),
                    r2_reason=[f"{p.get('type')} [{p.get('source')}]: {str(p.get('reason'))[:160]}" for p in g["check_r2"]["problems"]],
                    why="the r3 checks find no problem in this conversation; the r2 drop was a checker error")
            for a in att:
                if a is not g:
                    a["r3_note"] = "not used: another attempt of this session is kept"
                    dropped.append(a)
        else:
            for a in att:
                dropped.append(a)
                if a["r2_status"] == "kept":
                    rep("session_removed", persona=pid, session=sid, attempt=a.get("regenerated", 0),
                        why="kept in r2 but the r3 checks find a problem",
                        problems=[f"{p['type']} [{p['source']}]: {p['quote'][:80]} — {str(p['reason'])[:140]}" for p in a["check"]["problems"]])
            todo.append(sid)

    def regen(sid):
        base = attempts[sid][0]
        d0 = dt.date.fromisoformat(base["date"])
        n = max(a.get("regenerated", 0) for a in attempts[sid]) + 1
        ctx = copy.deepcopy(min(attempts[sid], key=lambda a: a.get("regenerated", 0))["context"])
        if "ctx.days" in ctx["elements"]:          # give the regenerated conversation exactly one date per day
            ctx["elements"]["ctx.days"]["text"] = re.sub(r" \([^)]*\)", "", ctx["elements"]["ctx.days"]["text"])
            ctx.pop("extra_dates", None)
            amend_fitness(ctx, d0, single=True)
        persona, flags = R.persona_at(pr, d0)
        pub = R.public_context(pr, d0, flags)
        g = simulate_r3(pr, base, ctx, pub, persona, n)
        if g is None:
            return sid, None
        g["check"] = check_v3(pr, g, pub["text"], ctx, f"{sid}_a{n}")
        g["r2_status"] = "new in r3"
        return sid, g

    with cf.ThreadPoolExecutor(4) as ex:
        for sid, g in ex.map(regen, todo):
            why = sorted({p["type"] for a in attempts[sid] for p in a["check"]["problems"]})
            if g and g["check"]["status"] == "ok":
                kept.append(g)
                rep("session_regenerated", persona=pid, session=sid, attempt=g["regenerated"], result="ok", real_problems_in_earlier_attempts=why)
            else:
                if g:
                    dropped.append(g)
                rep("session_regenerated", persona=pid, session=sid, attempt=g["regenerated"] if g else None, result="still not ok; left dropped",
                    real_problems_in_earlier_attempts=why,
                    problems=[f"{p['type']} [{p['source']}]: {p['quote'][:80]}" for p in (g["check"]["problems"] if g else [])])
    for s in kept:                        # rewrite recitals, then audit the rewritten session again
        if rewrite_recital(pr, s):
            s["check_before_rewrite"] = s["check"]
            s["check"] = check_v3(pr, s, pub_of(s)["text"], s["context"], f"{s['session_id']}_a{s.get('regenerated', 0)}_rw")
            if s["check"]["status"] != "ok":
                rep("rewritten_session_has_problem", persona=pid, session=s["session_id"],
                    problems=[f"{p['type']} [{p['source']}]: {p['quote'][:80]}" for p in s["check"]["problems"]])
    bad = [s for s in kept if s["check"]["status"] != "ok"]
    kept = [s for s in kept if s["check"]["status"] == "ok"]
    dropped += bad
    kept.sort(key=lambda s: s["date"])
    return {"persona_id": pid, "planned": H2["planned"], "kept": kept, "dropped": dropped, "standing": standing,
            "activities_covered": sorted({s["activity"] for s in kept}),
            "status": "ok" if len(kept) >= 12 and len({s["activity"] for s in kept}) == 6 else "failed",
            "r2_status": H2["status"], "r2_kept": [s["session_id"] for s in H2["kept"]]}


# ----------------------------------------------------------------------------------------------------- memory

def cue_status(label, link, basis):
    """source_supported_cue needs all three: the text suggests it, the entry is traced to a registered source, and
    that source derives from the attribute (or, for age, from our own child rule)."""
    if label in ("direct", "indirect"):
        if basis in ("unknown", "unregistered_detail"):
            return "unknown_source"
        return {"direct_source": "source_supported_cue", "co_generated": "source_supported_cue",
                "independent": "unsupported_association"}.get(link, "unverified_link")
    if label == "uncertain":
        return "uncertain"
    return "linked_not_apparent" if link in ("direct_source", "co_generated") and basis in ("registered", "mixed") else "none"


def build_memory(pr, hist, examples):
    pid = pr["persona_id"]
    stage = Counter()
    turns, order, claims_by_turn, el_by_session = {}, [], defaultdict(list), {}
    for s in hist["kept"]:
        d0 = dt.date.fromisoformat(s["date"])
        el_by_session[s["session_id"]] = detailed_elements(pr, d0, s["context"])
        for t in s["turns"]:
            turns[t["dia_id"]] = t
            order.append(t["dia_id"])
        for c in s["check"]["claims"]:
            claims_by_turn[c["dia_id"]].append({**c, "session": s["session_id"]})
    n_log = len(P1.LOG[pid])
    with cf.ThreadPoolExecutor(4) as ex:
        rows = [r for rs in ex.map(lambda s: R.extract_session(ARGS, pid, s, examples), hist["kept"]) for r in rs]
    fmt = Counter(e.get("reason") for e in P1.LOG[pid][n_log:] if e["kind"] == "memory_row_dropped")
    stage["1_rows_returned_by_extraction"] = len(rows) + sum(fmt.values())
    stage["2_rows_passing_format_checks"] = len(rows)

    def sup(job):
        i, it = job
        cl = [c for d in it["dialogue_ids"] for c in claims_by_turn[d]]
        prompt = T.SUPPORT_PROMPT.format(entry=it["text"], scope=it["scope"], plural="s" if len(it["dialogue_ids"]) > 1 else "",
                                         evidence=R.evidence_text(turns, order, it["dialogue_ids"]),
                                         claims="\n".join(f"- {c['cid']}: \"{c['quote']}\"" for c in cl) or "- (none)")
        try:
            out, _ = ask(ARGS, [{"role": "user", "content": prompt}], cseed(ARGS, pid, "support3", i), pid, f"support_r{i + 1:03d}", json_mode=True, temperature=0.0)
            r = as_json(out)
        except Exception:
            r = {}
        ids = [x for x in r.get("statements", []) if x in {c["cid"] for c in cl}] if isinstance(r.get("statements"), list) else []
        used = [c for c in cl if c["cid"] in ids]
        kinds = {c["kind"] for c in used}
        basis = ("unknown" if not used else "registered" if kinds == {"registered"} else
                 "unregistered_detail" if "registered" not in kinds else "mixed")
        sid = it["sessions"][0]
        els = sorted({f"{sid}/{e}" if e.startswith("ctx.") else e for c in used for e in c["elements"]})
        return {"supported": r.get("supported") if r.get("supported") in ("yes", "partly", "no") else "unparsed",
                "scope": r.get("scope") if r.get("scope") in ("one_off", "stable") else it["scope"], "reason": str(r.get("reason", ""))[:240],
                "statements": [{"session": sid, "cid": c["cid"], "dia_id": c["dia_id"], "quote": c["quote"], "kind": c["kind"], "elements": c["elements"]} for c in used],
                "basis": basis, "elements": els}

    with cf.ThreadPoolExecutor(4) as ex:
        checks = list(ex.map(sup, list(enumerate(rows))))
    items, all_el, sup_counts = [], {}, Counter()
    for it, c in zip(rows, checks):
        sup_counts[c["supported"]] += 1
        if c["supported"] == "no":
            P1.log(pid, "memory_row_dropped", reason="evidence does not support the entry", row=it["text"], evidence=it["quotes"][0], why=c["reason"])
            continue
        if c["scope"] != it["scope"]:
            stage["scope_corrected"] += 1
        sid = it["sessions"][0]
        for e in c["elements"]:
            all_el[e] = el_by_session[sid][e.split("/")[-1]]
        items.append({**it, "scope": c["scope"], "quote_support": c["supported"], "support_reason": c["reason"], "statements": c["statements"],
                      "fact_basis": c["basis"], "elements": c["elements"],
                      "occurrences": [{"session": sid, "date": it["date"], "dia_id": it["dialogue_ids"][0], "quote": it["quotes"][0], "text": it["text"]}]})
    stage["3_rows_after_quote_support_check"] = len(items)

    def fold(a, b, how):
        for k in ("dialogue_ids", "quotes", "sessions", "elements", "statements", "occurrences"):
            a[k] = a[k] + [x for x in b[k] if k in ("quotes", "occurrences") or x not in a[k]]
        a["scope"] = "stable" if "stable" in (a["scope"], b["scope"]) else "one_off"
        a["quote_support"] = "partly" if "partly" in (a["quote_support"], b["quote_support"]) else a["quote_support"]
        order_b = ["registered", "mixed", "unregistered_detail", "unknown"]
        if a["fact_basis"] != b["fact_basis"]:
            a["fact_basis"] = "mixed" if {a["fact_basis"], b["fact_basis"]} & {"registered", "mixed"} else max(a["fact_basis"], b["fact_basis"], key=order_b.index)
        P1.log(pid, "memory_duplicate_merged", how=how, kept=a["text"], merged=b["text"])

    merged = []
    for it in items:
        w = set(re.findall(r"[a-z0-9']+", it["text"].lower()))
        dup = next((o for o in merged if len(w & o["_w"]) / max(1, len(w | o["_w"])) >= 0.8), None)
        if dup:
            fold(dup, it, "word overlap")
            stage["merged_word_overlap"] += 1
        else:
            merged.append({**it, "_w": w})
    for i, o in enumerate(merged, 1):
        o.pop("_w")
        o["memory_id"] = f"x{i:03d}"
    by = {o["memory_id"]: o for o in merged}
    pairs = [(g[0], other) for g in R.duplicate_groups(ARGS, pid, merged, "r3") for other in g[1:]]

    def same(pair):
        a, b = by[pair[0]]["text"], by[pair[1]]["text"]
        try:
            out, _ = ask(ARGS, [{"role": "user", "content": T.PAIR_DUPLICATE_PROMPT.format(a=a, b=b)}], cseed(ARGS, pid, "pair", a, b), pid,
                         f"pair_{pair[0]}_{pair[1]}", json_mode=True, temperature=0.0)
            return str(as_json(out).get("same", "")).lower() == "yes"
        except Exception:
            return False

    with cf.ThreadPoolExecutor(4) as ex:
        verdicts = list(ex.map(same, pairs))
    gone = set()
    for (a, b), v in zip(pairs, verdicts):
        stage["duplicate_pairs_proposed"] += 1
        if v and a not in gone and b not in gone:
            fold(by[a], by[b], "semantic (group proposal confirmed pairwise)")
            gone.add(b)
            stage["merged_semantic"] += 1
        elif not v:
            P1.log(pid, "memory_merge_rejected", kept=by[a]["text"], not_merged=by[b]["text"], reason="pairwise check: not the same content")
    final = [o for o in merged if o["memory_id"] not in gone]
    for i, o in enumerate(final, 1):
        o["memory_id"] = f"m{i:03d}"
        o["n_sessions"] = len(set(o["sessions"]))
        o["n_occurrences"] = len(o["occurrences"])
    stage["4_entries_after_merging_duplicates"] = len(final)

    def ann(it):
        link = R.link_of(all_el, it["elements"]) if it["elements"] else {a: "unknown" for a in ATTRS}
        a = R.annotate(ARGS, pid, it["text"], it["quotes"][0], it["memory_id"], link)
        a["status"] = {f: cue_status(a["text_label"][f], link[f], it["fact_basis"]) for f in ATTRS}
        return a

    with cf.ThreadPoolExecutor(4) as ex:
        for it, a in zip(final, ex.map(ann, final)):
            it["annotation"] = a
    age_cue = [it for it in final if it["annotation"]["text_label"]["age"] != "direct"]
    removed = [{"memory_id": it["memory_id"], "text": it["text"], "reason": "direct age statement (entry removed whole; no mixed entry occurred)"}
               for it in final if it["annotation"]["text_label"]["age"] == "direct"]
    stage["5_entries_in_age_cue_only"] = len(age_cue)
    return {"raw": final, "age_cue_only": {"memory": age_cue, "removed": removed}, "stage_counts": dict(stage),
            "format_drops": dict(fmt), "quote_support_counts": dict(sup_counts), "source_elements": all_el}


# ------------------------------------------------------------------------------------------------------- view

def view(pr, cat, hist, mem, tasks):
    pid = pr["persona_id"]
    V = [f"# {pid} — ProfileFoundry {pr['source']['profile_id']} (r3, repaired from r2)\n",
         f"History: **{hist['status']}** — {len(hist['kept'])} sessions kept of {hist['planned']} planned (r2: {hist['r2_status']}, {len(hist['r2_kept'])} kept)\n",
         "## 1. Profile with provenance\n", "| field | value | source | basis |", "|---|---|---|---|"]
    for k, v in pr["fields"].items():
        V.append(f"| {k} | {json.dumps(v['value'], ensure_ascii=False)} | {v['source']} | {v['basis']} |")
    V += ["\n## 2. History sessions kept\n",
          "The assistant was given the date, a calendar and the home city; not the profile or the situation. "
          "Under each user message: the audited statements and where each comes from.\n"]
    for s in hist["kept"]:
        tag = ("restored in r3" if s["r2_status"] == "dropped" else "generated in r3" if s["r2_status"] == "new in r3" else "as in r2")
        V.append(f"**{s['session_id']} — {dtext(dt.date.fromisoformat(s['date']))} — {s['activity']}** ({s['errand']}) — *{tag}*"
                 + (" — *user message rewritten*" if s.get("rewritten_in_r3") else ""))
        V.append("> situation (synthetic_task_context): " + " | ".join(e["text"] for e in s["context"]["elements"].values()))
        for t in s["turns"]:
            V.append(f"- `{t['dia_id']}` **{t['speaker']}**: {t['text']}")
            for c in s["check"]["claims"]:
                if c["dia_id"] == t["dia_id"]:
                    V.append(f"    - {c['cid']} [{c['kind']}{': ' + ', '.join(c['elements']) if c['elements'] else ''}] “{c['quote']}”")
        for ch in s.get("rewritten_in_r3", []):
            V.append(f"    - rewrite of `{ch['dia_id']}` — before: “{ch['before']}”")
        V.append("")
    V += ["### Sessions not kept\n", "| session | attempt | r2 | r3 result |", "|---|---|---|---|"]
    for s in sorted(hist["dropped"], key=lambda s: (s["session_id"], s.get("regenerated", 0))):
        why = s.get("r3_note") or "; ".join(f"{p['type']} [{p['source']}]: “{p['quote'][:60]}” {str(p['reason'])[:120]}" for p in s["check"]["problems"]) or s["check"]["status"]
        V.append(f"| {s['session_id']} ({s['activity']}) | {s.get('regenerated', 0)} | {s['r2_status']} | {why} |")
    V += ["\n## 3. Memory with its support chain\n",
          "`quote` = does the user's cited message say it (yes/partly). `basis` = were the user statements behind it registered before the "
          "conversation (registered / mixed / unregistered_detail / unknown). Attribute cells: text label → status.\n",
          "| id (evidence) | memory | scope ×occurrences | quote | basis | sources | age | household | employment | income | education |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    cell = lambda a, f: "" if a["text_label"][f] == "none" and a["status"][f] == "none" else f"{a['text_label'][f]} → {a['status'][f]}"
    for it in mem["raw"]:
        a = it["annotation"]
        V.append(f"| {it['memory_id']} ({','.join(it['dialogue_ids'])}) | {it['text']} | {it['scope']} ×{it['n_occurrences']} | {it['quote_support']} | {it['fact_basis']} | "
                 f"{', '.join(it['elements']) or '—'} | " + " | ".join(cell(a, f) for f in ATTRS) + " |")
    V += [f"\n## 4. age_cue_only ({len(mem['age_cue_only']['memory'])} entries)\n",
          ("Removed: " + "; ".join(f"{r['memory_id']} “{r['text']}”" for r in mem["age_cue_only"]["removed"])) if mem["age_cue_only"]["removed"]
          else "No direct age statement in the memory; identical to section 3.",
          "\n## 5. Current tasks (unchanged from r2; statuses recomputed)\n", f"City: {tasks['city']}; catalog `{tasks['catalog']}`. {tasks['budget_rule']}\n",
          "| activity | request | constraints | text label → status |", "|---|---|---|---|"]
    for t in tasks["tasks"]:
        a = t["self_leak"]
        V.append(f"| {t['activity']} | {t['request']} | {json.dumps(t['constraints'])} | "
                 + (", ".join(f"{f}: {cell(a, f)}" for f in ATTRS if cell(a, f)) or "nothing") + " |")
    return "\n".join(V) + "\n"


# ------------------------------------------------------------------------------------------------------- main

def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--r2", default=os.path.join(ROOT, "data_v2_dialogue_preview_r2"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data_v2_dialogue_preview_r3"))
    ap.add_argument("--input", default=os.path.join(ROOT, "data_v2_preview", "pf", "us_households.jsonl"))
    ap.add_argument("--prev_manifest", default=os.path.join(ROOT, "data_v2_preview", "manifest.json"))
    ap.add_argument("--stage", default="regression", choices=["regression", "all"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default="qwen3:32b")
    ap.add_argument("--servers", default="http://localhost:11434=1")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--num_ctx", type=int, default=8192)
    ap.add_argument("--timeout", type=int, default=900)
    ARGS = args = ap.parse_args()
    P1.POOL = ServerPool(args.servers)
    os.makedirs(args.out, exist_ok=True)
    profiles = {p["persona_id"]: p for p in R.select_profiles(args)}
    results = regression(profiles)
    if args.stage == "regression":
        return
    if any(not r["passed"] for r in results):
        print("regression cases are not all passing; the checks are not applied to the data")
        return
    examples = T2.fact_examples(json.load(open(os.path.join(ROOT, "external", "upstream_templates", "locomo", "fact_generation_examples_new.json"))))
    for sub in ("history", os.path.join("memory", "raw"), os.path.join("memory", "filtered", "age_cue_only"), "tasks", "view", "personas", "catalogs", "templates"):
        os.makedirs(os.path.join(args.out, sub), exist_ok=True)
    for name in ("ASSISTANT_CHECK_PROMPT", "CLAIMS_PROMPT", "CONTRADICTION_CONFIRM_PROMPT", "SUPPORT_PROMPT", "PAIR_DUPLICATE_PROMPT", "REWRITE_PROMPT"):
        open(os.path.join(args.out, "templates", f"added_r3__{name}.txt"), "w").write(getattr(T, name))
    shutil.copy(os.path.join(HERE, "v2r3_regression_cases.json"), os.path.join(args.out, "regression_cases.json"))

    def run(pid):
        pr = profiles[pid]
        cat = json.load(open(os.path.join(args.r2, "catalogs", f"{pid}.json")))
        H2 = json.load(open(os.path.join(args.r2, "history", f"{pid}.json")))
        hist = repair_history(pr, cat, H2["standing"], H2)
        mem = build_memory(pr, hist, examples)
        tasks = json.load(open(os.path.join(args.r2, "tasks", f"{pid}.json")))
        for t in tasks["tasks"]:
            a = t["self_leak"]
            link = dict(a["generation_link"])
            kids = isinstance(pr["fields"]["own_minor_children"]["value"], list)
            if link["age"] == "co_generated" and not kids:
                link["age"] = "unverified"
            a["generation_link"] = link
            a["status"] = {f: cue_status(a["text_label"][f], link[f], "registered") for f in ATTRS}
        dump = lambda sub, obj: json.dump(obj, open(os.path.join(args.out, sub, f"{pid}.json"), "w"), indent=2, ensure_ascii=False)
        dump("personas", pr)
        dump("catalogs", cat)
        dump("history", hist)
        dump("tasks", tasks)
        dump(os.path.join("memory", "raw"), {"persona_id": pid, "memory": mem["raw"], "stage_counts": mem["stage_counts"], "format_drops": mem["format_drops"],
                                             "quote_support_counts": mem["quote_support_counts"], "source_elements": mem["source_elements"]})
        dump(os.path.join("memory", "filtered", "age_cue_only"), {"persona_id": pid, **mem["age_cue_only"]})
        open(os.path.join(args.out, "view", f"{pid}.md"), "w").write(view(pr, cat, hist, mem, tasks))
        print(f"{pid}: {hist['status']} kept {len(hist['kept'])} (r2 {len(H2['kept'])}); memory {mem['stage_counts']}", flush=True)

    with cf.ThreadPoolExecutor(8) as ex:
        list(ex.map(run, sorted(profiles)))
    json.dump(REPAIRS, open(os.path.join(args.out, "repair_log.json"), "w"), indent=2, ensure_ascii=False)
    json.dump(dict(P1.LOG), open(os.path.join(args.out, "failures_and_repairs.json"), "w"), indent=2, ensure_ascii=False)
    json.dump({"revision": 3, "built_from": "data_v2_dialogue_preview_r2 (read only)", "seed": args.seed, "model": args.model,
               "new_llm_calls": P1.STATS["llm_calls"],
               "code_sha256": {f: P1.sha(os.path.join(HERE, f)) for f in ("v2r3_repair.py", "v2r3_templates.py", "v2r2_dialogue_preview.py", "v2r2_templates.py")}},
              open(os.path.join(args.out, "manifest.json"), "w"), indent=2)
    print("done; new LLM calls:", P1.STATS["llm_calls"])


if __name__ == "__main__":
    main()
