"""Dataset v2 preview, version r4: fact graph + slot generation (same 8 personas, profiles, catalogs and session plans).

  1. graph     per persona, a fact graph (people, relations, life events, standing errand facts, preferences, catalog
               entities, sessions and their situations) built in code, plus deterministic consistency rules
  2. plan      per session, a dialogue plan in code: which facts (slots, each pointing to graph nodes) each user
               message says and what each assistant message does
  3. realise   the model only words each message; code then checks the words: every slot present, and no date,
               number, name, relation, diet/health or work detail that is not registered. A failing message is
               re-worded (up to 4 tries); a session that still fails is marked failed and not replaced
  4. audit     the r3 user-statement audit and assistant check are run as independent measurements (not as gates)
  5. memory    LoCoMo extraction; each entry is tied to the slots of the cited messages and through them to graph
               nodes; annotation as in r3 (text label + generation link + status)

Earlier versions are read only. Usage:
  python scripts/v2r4_preview.py --servers http://localhost:11436=4,http://localhost:11437=4
"""

import argparse
import concurrent.futures as cf
import copy
import datetime as dt
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import v2r3_repair as X                 # cached LLM call, r3 audit/checks, cue status
import v2r3_templates as T3
import v2r4_templates as T
from run_dev2 import ServerPool

R, P1 = X.R, X.P1
ATTRS, MONTHS, WEEKDAYS = R.ATTRS, R.MONTHS, R.WEEKDAYS
norm, as_json, cseed, dtext = R.norm, R.as_json, R.cseed, R.dtext
ARGS = None
LOG = defaultdict(list)
NUMW = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]


def log(pid, kind, **kw):
    with P1.LOCK:
        LOG[pid].append({"kind": kind, **kw})


def ordinal(n):
    return str(n) + ("th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


SYN = {"mother": "mother|mom|mum|mama", "father": "father|dad|papa", "son": "son", "daughter": "daughter", "brother": "brother|sibling",
       "sister": "sister|sibling", "wife": "wife|spouse|partner", "husband": "husband|spouse|partner", "partner": "partner|spouse"}


def rel_pat(word, child=False):
    """Words a person uses for a relative (so 'my mom' satisfies a slot about the user's mother)."""
    alts = SYN.get(word, re.escape(word))
    return rf"\b({alts})s?\b" + (r"|\bkids?\b|\bchild(ren)?\b" if child else "")


def L(**kw):
    return {a: kw.get(a, "independent") for a in ATTRS}


# =============================================================================================== 1. fact graph

def build_graph(pr, cat, standing, plan):
    pid = pr["persona_id"]
    f = {k: v["value"] for k, v in pr["fields"].items()}
    N, E = {}, []

    def node(nid, kind, link, **attrs):
        N[nid] = {"id": nid, "kind": kind, "link": link, **attrs}

    def edge(a, rel, b):
        E.append({"from": a, "rel": rel, "to": b})

    # the user's own node carries no attribute link: counting oneself reveals nothing, and age is never a slot in r4
    node("person:self", "person", L(), relation="self", given_name=f["given_name"], dob=f["date_of_birth"],
         age_at_reference=f["age"], gender=f["gender"], city=f["city"], marital_status=f["marital_status"], source="profilefoundry")
    spouse_name = next((e["text"].replace("married ", "").split()[0] for e in f["life_events"] if e["type"] == "marriage"), None)
    married = f["marital_status"] == "Married"
    for i, a in enumerate(f["co_resident_adults"], 1):
        rel = a["relation"]
        word = R.rel_label(a, married) or "housemate"
        nid = "person:partner" if rel == "partner" else f"person:home{i}"
        node(nid, "person", L(household_children="direct_source", age="unverified"), relation=rel, word=word, age_at_reference=a["age"],
             gender=a.get("gender"), lives_with_self=True, source="profilefoundry", profile_id=a["profile_id"],
             given_name=spouse_name if rel == "partner" else None)
        edge("person:self", {"partner": "partner_of", "parent": "child_of", "adult child": "parent_of", "sibling": "sibling_of"}.get(rel, "lives_with"), nid)
        edge("person:self", "lives_with", nid)
    for i, c in enumerate(f["own_minor_children"] if isinstance(f["own_minor_children"], list) else [], 1):
        nid = f"person:child{i}"
        node(nid, "person", L(household_children="direct_source", age="co_generated"), relation="minor child",
             word="son" if c["sex"] == "boy" else "daughter", age_at_reference=c["age"], lives_with_self=True, source="synthetic")
        edge("person:self", "parent_of", nid)
        edge("person:self", "lives_with", nid)
        if "person:partner" in N:
            edge("person:partner", "parent_of", nid)
    for i, c in enumerate(f["own_adult_children"], 1):
        if not c["co_resident"]:
            node(f"person:away{i}", "person", L(household_children="direct_source", age="unverified"), relation="adult child (elsewhere)",
                 age_at_reference=c["age"], lives_with_self=False, source="profilefoundry")
            edge("person:self", "parent_of", f"person:away{i}")
    node("person:friend", "person", L(), relation="friend", word="friend", source="synthetic", note="unnamed companion; not in ProfileFoundry")
    for i, e in enumerate(f["life_events"], 1):
        node(f"event:{i}", "event", L(age="unverified", household_children="unverified" if e["type"] in ("marriage", "divorce") else "independent"),
             date=e["date"], type=e["type"], text=e["text"], source="profilefoundry")
        edge("person:self", "has_event", f"event:{i}")
    for k in ("schedule", "music", "hobbies", "diet", "seating"):
        node(f"pref:{k}", "preference", L(), value=f["preferences"][k], source="synthetic")
    household_ids = [n for n in N if N[n].get("lives_with_self")]
    has_minor = any(N[n]["relation"] == "minor child" for n in household_ids)
    hl = L(household_children="direct_source", age="co_generated" if has_minor else "unverified") if household_ids else L()
    node("fact:household_size", "count", hl, value=1 + len(household_ids), source="derived")
    for k in ("carrier", "plan_data", "monthly_use_gb", "monthly_bill_usd", "grocery_service", "usual_items"):
        node(f"fact:{k}", "standing", L(), value=standing[k], source="synthetic_task_context")
    line_members = [n for n in household_ids if N[n]["relation"] in [x for x in standing["lines_kinds"]]] if standing["lines_kinds"] else []
    lines_link = (L(household_children="direct_source", age="co_generated" if any(N[n]["relation"] == "minor child" for n in line_members) else "unverified")
                  if line_members else L())
    node("fact:lines", "count", lines_link, value=standing["lines"], members=line_members, source="synthetic_task_context")
    for key in ("concerts", "restaurants", "gyms", "grocery_services", "mobile_plans", "weekend_destinations"):
        for it in cat[key]:
            node(f"catalog:{key}:{it['id']}", "catalog", L(), name=it.get("name") or it.get("venue") or it.get("carrier"), source="synthetic")
    for s in plan:
        node(f"session:{s['session_id']}", "session", L(), date=s["date"], activity=s["activity"], errand=s["errand"])
        edge("person:self", "has_session", f"session:{s['session_id']}")
    return {"persona_id": pid, "nodes": N, "edges": E}


def graph_checks(g, sessions):
    """Deterministic consistency rules over the fact graph (and the slot plans that point into it)."""
    N, E = g["nodes"], g["edges"]
    me = N["person:self"]
    ref = X.R.REFERENCE
    out = []

    def chk(rule, ok, detail=""):
        out.append({"rule": rule, "ok": bool(ok), "detail": detail})

    born = dt.date.fromisoformat(me["dob"])
    chk("self: age equals date of birth at the reference date", P1.age_on(me["dob"]) == me["age_at_reference"])
    for e in E:
        a, b = N.get(e["from"]), N.get(e["to"])
        chk(f"edge endpoints exist: {e['from']} {e['rel']} {e['to']}", a is not None and b is not None)
        if e["rel"] == "parent_of" and a and b and "age_at_reference" in b:
            chk(f"parent at least 15 years older: {e['from']} -> {e['to']}", a["age_at_reference"] - b["age_at_reference"] >= 15,
                f"{a['age_at_reference']} vs {b['age_at_reference']}")
        if e["rel"] == "child_of" and a and b and "age_at_reference" in b:
            chk(f"parent at least 15 years older: {e['to']} -> {e['from']}", b["age_at_reference"] - a["age_at_reference"] >= 15,
                f"{b['age_at_reference']} vs {a['age_at_reference']}")
    for nid, n in N.items():
        if n["kind"] == "event":
            d = dt.date.fromisoformat(n["date"])
            chk(f"{nid} between birth and reference date", born <= d <= ref, n["date"])
    moves = sorted((n for n in N.values() if n["kind"] == "event" and n["type"] == "move"), key=lambda n: n["date"])
    if moves:
        chk("last move matches current city", moves[-1]["text"] == f"moved to {me['city']}", moves[-1]["text"])
    partner = "person:partner" in N
    chk("partner node only if married or partnered", (not partner) or me["marital_status"] in ("Married", "Cohabiting", "Partnered"), me["marital_status"])
    hh = [n for n in N if N[n].get("lives_with_self")]
    chk("household size = 1 + people living with self", N["fact:household_size"]["value"] == 1 + len(hh))
    chk("phone-plan members live with self", all(m in hh for m in N["fact:lines"]["members"]))
    chk("phone lines = 1 + plan members", N["fact:lines"]["value"] == 1 + len(N["fact:lines"]["members"]),
        f"{N['fact:lines']['value']} vs {1 + len(N['fact:lines']['members'])}")
    sess = sorted((n for n in N.values() if n["kind"] == "session"), key=lambda n: n["date"])
    chk("sessions inside the history window", all(X.R.WINDOW[0].isoformat() <= n["date"] <= X.R.WINDOW[1].isoformat() for n in sess))
    for s in sessions:
        d0 = dt.date.fromisoformat(s["date"])
        for sl in s["slots"]:
            for nd in sl["nodes"]:
                chk(f"{s['session_id']} {sl['id']}: slot points to an existing node", nd in N, nd)
            if sl["key"].startswith("date"):
                d = dt.date.fromisoformat(sl["value"])
                chk(f"{s['session_id']} {sl['id']}: date within 0-45 days after the session", 0 <= (d - d0).days <= 45, sl["value"])
            if sl["key"] == "participants":
                chk(f"{s['session_id']} participants are self, friend or people living with self",
                    all(nd == "person:friend" or nd in hh for nd in sl["nodes"]), ", ".join(sl["nodes"]))
                cnt = next((x for x in s["slots"] if x["key"] == "count"), None)
                if cnt:
                    chk(f"{s['session_id']} count = 1 + participants", cnt["value"] == 1 + len(sl["nodes"]), f"{cnt['value']} vs {1 + len(sl['nodes'])}")
    return out


# =============================================================================================== 2. slot plans

def slot(sid, key, value, say, nodes, need, link=None):
    """need: list of regex alternatives groups; every group must match the message (each group is an OR)."""
    return {"id": sid, "key": key, "value": value, "say": say, "nodes": nodes, "need": need}


def date_slot(sid, key, d, node, d0=None):
    wd, mo = d.strftime("%A"), d.strftime("%B")
    near = d0 is not None and (d - d0).days < 7
    eg = f"this {wd}, the {ordinal(d.day)}" if near else f"{wd}, the {ordinal(d.day)} of {mo}"
    return slot(sid, key, d.isoformat(), f"the day: {wd}, {d.day} {mo} (say the weekday and the day number, e.g. '{eg}')",
                [node], [rf"\b{d.day}(?:st|nd|rd|th)?\b", rf"\b({wd}|{wd[:3]}|{mo}|{mo[:3]})\b"])


def time_slot(sid, t, node):
    h, m = t.split(":")
    hh = str(int(h) % 12 or 12)
    pat = rf"\b{hh}:{m}\b|\b{hh}\.{m}\b" + (r"|half past" if m == "30" else rf"|\b{hh}\s?(?:pm|am|p\.m\.|a\.m\.|o'clock)|\b{hh}\b")
    return slot(sid, "time", t, f"the time: about {hh}:{m} {'pm' if int(h) >= 12 else 'am'}", [node], [pat])


def count_slot(sid, n, nodes, what="people"):
    pat = rf"\b{n}\b|\b{NUMW[n]}\b" if n <= 10 else rf"\b{n}\b"
    if n == 1:
        pat += r"|just me|by myself|alone|myself|solo|single|only me|on my own"
    if n == 2:
        pat += r"|couple|both of us|the two of us|pair"
    sl = slot(sid, "count", n, f"how many {what}: {n}", nodes, [pat])
    sl["what"] = what.split(" (")[0]
    return sl


def build_slots(g, pr, s, rng):
    """Structured situation + who comes, from the graph. Same sampling rules as r2 (participants uniform over the
    relation types that exist, never looking at age); optional preferences included with probability 0.7."""
    N = g["nodes"]
    d0 = dt.date.fromisoformat(s["date"])
    act, k = s["activity"], R.ERRANDS[s["activity"]].index(s["errand"])
    sess = f"session:{s['session_id']}"
    S = []
    nid = lambda: f"s{len(S) + 1}"
    hh = [n for n in N if N[n].get("lives_with_self")]
    partner = "person:partner" if "person:partner" in N else None
    kids = [n for n in hh if N[n]["relation"] == "minor child"]
    pick_cat = lambda key: rng.choice([n for n in N if n.startswith(f"catalog:{key}:")])
    pref = lambda key: N[f"pref:{key}"]["value"]

    def participants(allow_family=True):
        opts = [("alone", []), ("friend", ["person:friend"])]
        if partner:
            opts.append(("partner", [partner]))
        fam = [n for n in hh if N[n]["relation"] != "other adult (relation not recorded)"]
        if allow_family and fam and (len(fam) >= 2 or not partner):
            opts.append(("household family", fam))
        kind, members = rng.choice(opts)
        if kind == "alone":
            return kind, members
        words, need = [], []
        for m in members:
            n = N[m]
            age_txt = f"{n['age_at_reference']}-year-old " if n["relation"] == "minor child" and act != "fitness_class_booking" else ""
            words.append(f"your {age_txt}{n['word']}")
            need.append(rel_pat(n["word"], child=n["relation"] in ("minor child", "adult child")))
            if age_txt:
                need.append(rf"\b{n['age_at_reference']}\b|\b{NUMW[n['age_at_reference']] if n['age_at_reference'] <= 10 else 'x'}\b")
        S.append(slot(nid(), "participants", kind, "who is coming besides you: " + ", ".join(words), members, need))
        return kind, members

    def add_pref(key, say, need, p=0.7):
        if rng.random() < p:
            S.append(slot(nid(), f"pref_{key}", pref(key), say, [f"pref:{key}"], need))

    def schedule_pref():
        v = pref("schedule")
        need = {"prefers morning activities": r"morning", "enjoys late-night events": r"late", "prefers evening events": r"evening",
                "prefers afternoon events and being home by 9 pm": r"afternoon|9"}[v]
        add_pref("schedule", f"a time preference: you {v.replace('prefers', 'prefer').replace('enjoys', 'enjoy')}", [need])

    def diet_pref():
        v = pref("diet")
        if v != "no restrictions":
            need = {"vegetarian": "vegetarian", "gluten-free": "gluten", "no shellfish": "shellfish", "low-sodium": r"low[- ]sodium|salt",
                    "lactose intolerant": r"lactose|dairy"}[v]
            add_pref("diet", f"your diet: {v}", [need])

    S.append(slot(nid(), "request", s["errand"], f"what you want: {s['errand']}", [sess], []))
    if act == "concert_ticket_booking":
        day = R.next_weekday(d0, ("Friday", "Saturday", "Sunday"), 3, 16, rng)
        if k == 2:
            v = pick_cat("concerts")
            new = R.next_weekday(day, ("Friday", "Saturday", "Sunday"), 5, 16, rng)
            S.append(slot(nid(), "venue", N[v]["name"], f"the venue of the show you hold seats for: {N[v]['name']}", [v], [re.escape(N[v]["name"].replace("The ", ""))]))
            S.append(date_slot(nid(), "date_held", day, sess, d0))
            if rng.random() < 0.5:
                S.append(date_slot(nid(), "date_wanted", new, sess, d0))
            else:
                S.append(slot(nid(), "change", "aisle", "what you want changed: seats closer to the aisle", [sess], [r"aisle"]))
        else:
            S.append(date_slot(nid(), "date", day, sess, d0))
            add_pref("music", f"the kind of music: {' or '.join(pref('music'))}", ["|".join(re.escape(m) for m in pref("music"))])
            if pref("seating") != "no seating preference":
                add_pref("seating", f"seating: you {pref('seating').replace('prefers', 'prefer')}", [r"aisle|seat"])
            schedule_pref()
        kind, members = participants()
        S.append(count_slot(nid(), 1 + len(members), ["person:self"] + members, "tickets"))
    elif act == "restaurant_reservation":
        kind, members = participants()
        if k == 2:
            v = pick_cat("restaurants")
            day = d0 + dt.timedelta(days=rng.randint(1, 5))
            old, new = rng.sample(["18:00", "18:30", "19:00", "19:30", "20:00", "20:30", "21:00"], 2)
            S.append(slot(nid(), "venue", N[v]["name"], f"the restaurant where you have a reservation: {N[v]['name']}", [v], [re.escape(N[v]["name"].replace("The ", ""))]))
            S.append(date_slot(nid(), "date", day, sess, d0))
            S.append(time_slot(nid(), old, sess))
            S[-1]["say"] = S[-1]["say"].replace("the time", "the time of the reservation now")
            S.append(time_slot(nid(), new, sess))
            S[-1]["say"] = S[-1]["say"].replace("the time", "the new time you want")
        else:
            day = d0 + dt.timedelta(days=rng.randint(1, 8)) if k == 0 else R.next_weekday(d0, ("Saturday", "Sunday"), 1, 8, rng)
            S.append(date_slot(nid(), "date", day, sess, d0))
            S.append(time_slot(nid(), rng.choice(["18:00", "18:30", "19:00", "19:30", "20:00"] if k == 0 else ["11:30", "12:00", "12:30", "13:00"]), sess))
            if k == 0 and rng.random() < 0.6:
                v = pick_cat("restaurants")
                S.append(slot(nid(), "venue", N[v]["name"], f"the restaurant you have in mind: {N[v]['name']}", [v], [re.escape(N[v]["name"].replace("The ", ""))]))
            diet_pref()
        S.append(count_slot(nid(), 1 + len(members), ["person:self"] + members))
    elif act == "fitness_class_booking":
        v = pick_cat("gyms")
        cls = rng.choice(["yoga", "spin", "strength training", "pilates", "swimming", "indoor climbing"])
        S.append(slot(nid(), "class", cls, f"the class you want to try: {cls}", [sess], [re.escape(cls.split()[-1])]))
        if k == 0:
            S.append(slot(nid(), "venue", N[v]["name"], f"the gym: {N[v]['name']}", [v], [re.escape(N[v]["name"].split()[0])]))
        start = R.next_weekday(d0, ("Monday",), 1, 8, rng) if k == 1 else d0 + dt.timedelta(days=1)
        days = sorted(rng.sample(range(7), 2))
        for j, off in enumerate(days):
            S.append(date_slot(nid(), f"date{j + 1}", start + dt.timedelta(days=off), sess, d0))
        schedule_pref()
        participants(allow_family=False)
    elif act == "weekend_trip_booking":
        fri = R.next_weekday(d0, ("Friday",), 7, 30, rng)
        S.append(date_slot(nid(), "date_from", fri, sess, d0))
        S.append(date_slot(nid(), "date_to", fri + dt.timedelta(days=2), sess, d0))
        if rng.random() < 0.7:
            v = pick_cat("weekend_destinations")
            S.append(slot(nid(), "destination", N[v]["name"], f"where you are thinking of going: {N[v]['name']}", [v], [re.escape(N[v]["name"])]))
        tr = rng.choice(["drive", "train or bus"])
        S.append(slot(nid(), "transport", tr, f"how you would travel: {'by car' if tr == 'drive' else 'by train or bus'}", [sess],
                      [r"driv|car" if tr == "drive" else r"train|bus"]))
        if k == 0:
            lodg = rng.choice(["hotel", "cabin", "vacation rental"])
            S.append(slot(nid(), "lodging", lodg, f"the kind of place to stay: {lodg}", [sess], [lodg.split()[-1]]))
        add_pref("hobbies", f"something you would like to do there: {rng.choice(pref('hobbies'))}", [])
        if S[-1]["key"] == "pref_hobbies":
            S[-1]["need"] = [re.escape(S[-1]["say"].split(": ")[1].split()[0][:5])]
        kind, members = participants()
        S.append(count_slot(nid(), 1 + len(members), ["person:self"] + members, "travellers"))
    elif act == "grocery_delivery":
        sv = N["fact:grocery_service"]["value"]
        S.append(slot(nid(), "service", sv, f"the grocery service you use: {sv}", ["fact:grocery_service"], [re.escape(sv)]))
        day = d0 + dt.timedelta(days=rng.randint(1, 4))
        S.append(date_slot(nid(), "date", day, sess, d0))
        part = rng.choice(["morning", "afternoon", "evening"])
        S.append(slot(nid(), "slot", part, f"the delivery slot: {part}", [sess], [part]))
        if k in (1, 2):
            items = N["fact:usual_items"]["value"] if k == 1 else rng.sample(["rice", "lentils", "spinach", "apples", "potatoes", "carrots", "olive oil", "bananas", "tomatoes", "onions"], 4)
            S.append(slot(nid(), "items", items, ("your usual items: " if k == 1 else "items to add: ") + ", ".join(items),
                          ["fact:usual_items"] if k == 1 else [sess], [re.escape(i.split()[-1].rstrip("s")) for i in items]))
        if rng.random() < 0.5 and N["fact:household_size"]["value"] > 1:
            S.append(count_slot(nid(), N["fact:household_size"]["value"], ["fact:household_size"], "people the order is for (everyone at home)"))
        diet_pref()
    else:
        c = N["fact:carrier"]["value"]
        S.append(slot(nid(), "carrier", c, f"your current carrier: {c}", ["fact:carrier"], [re.escape(c.split()[0])]))
        pdata = N["fact:plan_data"]["value"]
        S.append(slot(nid(), "plan_data", pdata, f"your current plan's data: {pdata}", ["fact:plan_data"],
                      [r"unlimited" if pdata == "unlimited" else rf"\b{pdata.split()[0]}\s?(GB|gig)"]))
        u = N["fact:monthly_use_gb"]["value"]
        S.append(slot(nid(), "usage", u, f"how much data you use: about {u} GB a month", ["fact:monthly_use_gb"], [rf"\b{u}\b"]))
        b = N["fact:monthly_bill_usd"]["value"]
        S.append(slot(nid(), "bill", b, f"your monthly bill: about ${b}", ["fact:monthly_bill_usd"], [rf"\b{b}\b"]))
        ln = N["fact:lines"]
        who = ", ".join("your " + N[m]["word"] for m in ln["members"])
        S.append(count_slot(nid(), ln["value"], ["fact:lines"] + ln["members"], "lines on the plan"))
        if ln["members"]:
            S[-1]["say"] += f" (you and {who})"
            S[-1]["need"] += [rel_pat(N[m]["word"], child=N[m]["relation"] in ("minor child", "adult child")) + r"|\bfamily\b" for m in ln["members"]][:1]
        reason = rng.choice([("the bill went up recently", r"bill|went up|increase|higher"), ("you want more data", r"data"),
                             ("calls drop at home sometimes", r"drop"), ("you want to pay less", r"cheap|less|lower|save")])
        S.append(slot(nid(), "reason", reason[0], f"why: {reason[0]}", [sess], [reason[1]]))
    return S


ASK = {"date": "which day they have in mind", "date_held": "which date the show is on", "date_wanted": "which date they would prefer instead",
       "date1": "which days suit them", "date2": "which days suit them", "date_from": "which dates they want to travel",
       "date_to": "which dates they want to travel", "time": "what time suits them", "count": "how many people (or tickets, lines) it is for",
       "participants": "who is coming", "venue": "which place they have in mind", "class": "which class they want", "destination": "where they want to go",
       "transport": "how they want to travel", "lodging": "what kind of place they want to stay in", "service": "which grocery service they use",
       "slot": "which delivery slot suits them", "items": "which items they want", "carrier": "which carrier they are with",
       "plan_data": "how much data their plan has", "usage": "how much data they use", "bill": "how much they pay", "reason": "why they want to change",
       "change": "what they would like to change"}


def make_plan(S, rng):
    """Split the slots into 2-3 user messages; the assistant asks about the next message's first slot, and finally
    sums up what it will look for."""
    core = [s for s in S if s["key"] in ("request",) or s["key"].startswith("date")]
    rest = [s for s in S if s not in core]
    rng.shuffle(rest)
    first_extra = rest[:rng.randint(0, min(2, len(rest)))]
    rest = rest[len(first_extra):]
    groups = [core + first_extra]
    n_more = 1 if len(rest) <= 2 else 2
    if rest:
        cut = (len(rest) + 1) // 2 if n_more == 2 else len(rest)
        groups.append(rest[:cut])
        if rest[cut:]:
            groups.append(rest[cut:])
    turns = []
    for i, gp in enumerate(groups):
        turns.append({"speaker": "User", "slots": [x["id"] for x in gp]})
        if i + 1 < len(groups):
            nxt = groups[i + 1][0]
            q = f"how many {nxt['what']} it is for" if nxt["key"] == "count" else ASK.get(nxt["key"].replace("pref_", ""), "about " + nxt["say"].split(":")[0])
            turns.append({"speaker": "Assistant", "act": f"briefly acknowledge, then ask the user {q}",
                          "asks": nxt["id"]})
        else:
            turns.append({"speaker": "Assistant", "act": "say briefly what you will look for, using only details the user gave"})
    return turns


# =============================================================================================== 3. realise + code check

RELATION_WORDS = r"\b(wife|husband|partner|spouse|sons?|daughters?|kids?|child(?:ren)?|mom|mother|dad|father|parents?|brothers?|sisters?|siblings?|friends?|family|roommates?|housemates?|grandkids?|grandchildren|baby|toddler|nephew|niece|cousin|aunt|uncle|boyfriend|girlfriend|fianc[eé]e?)\b"
DIET_WORDS = r"\b(vegetarian|vegan|gluten|shellfish|lactose|dairy|low[- ]sodium|sodium|salt|allerg\w*|diabet\w*|keto|halal|kosher|nut)\b"
WORK_WORDS = r"\b(my job|at work|after work|before work|I work|my work|my shift|shifts|my office|my boss|coworkers?|colleagues?|retired|retirement|my school|college|university|my students|my clients)\b"


def allowed_relation_words(N, S):
    words = set()
    for sl in S:
        for nd in sl["nodes"]:
            n = N.get(nd, {})
            w = n.get("word")
            if w:
                words.add(w)
                if n.get("relation") in ("minor child", "adult child"):
                    words |= {"kid", "kids", "child", "children", "son" if w == "son" else "daughter"}
                if w in ("mother", "father"):
                    words |= {"mom", "mum", "mama", "dad", "papa", "parent", "parents"}
                if w in ("wife", "husband"):
                    words |= {"spouse", "partner"}
                if w in ("brother", "sister"):
                    words |= {"sibling", "siblings"}
        if sl["key"] in ("participants",) and sl["value"] == "household family":
            words.add("family")
        if sl["key"] == "count" and any(nd == "fact:household_size" for nd in sl["nodes"]):
            words |= {"family", "household"}
        if sl["key"] == "count" and any(nd == "fact:lines" for nd in sl["nodes"]) and len(sl["nodes"]) > 1:
            words |= {"family"}
    return {w.rstrip("s") for w in words} | words


def check_message(pr, g, cat, s, S, turns_so_far, msg, text):
    """Deterministic checks of one realised message. Returns a list of problems (empty = accept)."""
    N = g["nodes"]
    d0 = dt.date.fromisoformat(s["date"])
    probs = []
    said = [x for t in turns_so_far for x in t.get("slots", [])]
    mine = [x for x in S if x["id"] in msg.get("slots", [])]
    visible = [x for x in S if x["id"] in said + msg.get("slots", [])] if msg["speaker"] == "Assistant" else \
        [x for x in S if x["id"] in said + msg["slots"]]
    for sl in mine:
        for pat in sl["need"]:
            if pat and not re.search(pat, text, re.I):
                probs.append(f"missing slot {sl['id']} ({sl['key']}): pattern /{pat}/ not found")
    # dates: every day+month mention and every weekday must belong to a registered date of this session
    reg = {dt.date.fromisoformat(x["value"]) for x in S if x["key"].startswith("date")}
    for raw, c in X.date_mentions(text, d0):
        if c not in reg:
            probs.append(f"date not registered: {raw}")
    for m in re.finditer(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b", text):
        if m.group(1)[:3] not in {d.strftime("%a") for d in reg}:
            probs.append(f"weekday not registered: {m.group(1)}")
    for m in re.finditer(r"\bthe (\d{1,2})(?:st|nd|rd|th)\b", text):
        if int(m.group(1)) not in {d.day for d in reg}:
            probs.append(f"day number not registered: {m.group(0)}")
    probs += [f"weekday/date mismatch: {p['quote']}" for p in R.date_problems([{"dia_id": "-", "speaker": msg["speaker"], "text": text}], d0)]
    # numbers: every number must come from a slot visible to this speaker (or a registered date/time)
    allowed_nums = set()
    for x in visible:
        allowed_nums |= set(re.findall(r"\d+", str(x["value"]) + " " + x["say"]))
    allowed_nums |= {str(d.day) for d in reg} | {str(d.year) for d in reg}
    vis_text = " ".join(x["say"] + " " + str(x["value"]) for x in visible).lower()
    allowed_nums |= {str(i) for i, w_ in enumerate(NUMW) if re.search(rf"\b{w_}\b", vis_text)}
    for m in re.finditer(r"(?<![\w:.])(\d+)(?![\w:])", text.replace(",", "")):
        if m.group(1) not in allowed_nums:
            probs.append(f"number not registered: {m.group(1)}")
    for w, n in zip(NUMW[2:], range(2, 11)):
        if re.search(rf"\b{w}\b", text, re.I) and str(n) not in allowed_nums and not re.search(rf"\b{w} (of us|or)\b", text, re.I):
            probs.append(f"number word not registered: {w}")
    # names: capitalised names must come from the slots, the conversation so far, the city or the catalog
    base = " ".join(x["say"] + " " + str(x["value"]) for x in visible) + " " + " ".join(t["text"] for t in turns_so_far) + " " + \
        pr["fields"]["city"]["value"] + " " + X.STATES.get(pr["fields"]["city"]["value"].split(", ")[-1], "")
    aw = {w.lower() for w in re.findall(r"[A-Za-z][a-z]+", base)}
    nn = X.new_names(text, aw)
    if nn:
        probs.append(f"name not registered: {', '.join(nn[:3])}")
    if re.search(rf"\b{re.escape(pr['fields']['given_name']['value'])}\b", text):
        probs.append("uses the user's own name")
    # relations, diet/health, work
    rels = {m.group(1).lower() for m in re.finditer(RELATION_WORDS, text, re.I)}
    ok_rel = allowed_relation_words(N, visible)
    bad = sorted(r for r in rels if r not in ok_rel and r.rstrip("s") not in ok_rel)
    if bad:
        probs.append(f"relation not registered: {', '.join(bad)}")
    diet_ok = " ".join(x["say"] for x in visible if x["key"] in ("pref_diet",))
    for m in re.finditer(DIET_WORDS, text, re.I):
        if not re.search(re.escape(m.group(1)[:4]), diet_ok, re.I):
            probs.append(f"diet/health detail not registered: {m.group(1)}")
            break
    m = re.search(WORK_WORDS, text, re.I)
    if m:
        probs.append(f"work/school detail: {m.group(1)}")
    if msg["speaker"] == "User":
        m = re.search(X.RELATIVE_HEALTH_RE, text, re.I)
        if m:
            probs.append(f"diet/health need attributed to someone else: {m.group(0)}")
        m = re.search(X.HELPER_VOICE_RE, text, re.I)
        if m:
            probs.append(f"helper voice in a user message: {m.group(0)}")
    else:
        for pat, what in ((X.COMPLETION_RE, "completion claim"), (X.BRAND_RE, "real company"), (X.CONTACT_RE, "contact detail")):
            m = re.search(pat, text, re.I)
            if m and not (what == "completion claim" and re.search(X.INTENT_RE, X.sentence_before(text, m.start()), re.I)):
                probs.append(f"{what}: {m.group(0)}")
        if re.search(r"\b(I've|I have) (booked|reserved|ordered|changed|confirmed|set up|added|placed)\b", text, re.I):
            probs.append("completion claim")
    return sorted(set(probs))


def render(turns):
    return "\n".join(f"{'User' if t['speaker'] == 'User' else 'Assistant'}: {t['text']}" for t in turns) or "(nothing yet)"


def realise_session(pr, g, cat, s, S, plan):
    pid = pr["persona_id"]
    turns = []
    first = pr["fields"]["given_name"]["value"]
    n = int(s["session_id"][1:])
    for i, msg in enumerate(plan):
        tries = []
        for k in range(4):
            if msg["speaker"] == "User":
                facts = "\n".join(f"- {x['say']}" for x in S if x["id"] in msg["slots"])
                prompt = T.USER_REALISE_PROMPT.format(name=first, errand=s["errand"], conversation=render(turns), facts=facts)
            else:
                prompt = T.ASSISTANT_REALISE_PROMPT.format(errand=s["errand"], conversation=render(turns), act=msg["act"])
            if tries:
                prompt += "\n\nYour previous attempt was rejected because: " + "; ".join(tries[-1]["problems"]) + ". Fix exactly that."
            try:
                out, _ = X.ask(ARGS, [{"role": "user", "content": prompt}], cseed(ARGS, pid, "r4real", s["session_id"], i, k), pid,
                               f"realise_{s['session_id']}_{i + 1}_{k}", temperature=0.7)
                text = R.clean(out)
            except Exception as e:
                text, out = "", str(e)
            probs = check_message(pr, g, cat, s, S, turns, msg, text) if text else ["empty reply"]
            tries.append({"text": text, "problems": probs})
            if not probs:
                break
        if tries[-1]["problems"]:
            log(pid, "message_failed", session=s["session_id"], turn=i + 1, speaker=msg["speaker"], attempts=tries)
            return None, tries, turns
        if len(tries) > 1:
            log(pid, "message_reworded", session=s["session_id"], turn=i + 1, speaker=msg["speaker"], rejected=tries[:-1])
        turns.append({"dia_id": f"D{n}:{i + 1}", "speaker": msg["speaker"], "text": tries[-1]["text"], "slots": msg.get("slots", []),
                      "act": msg.get("act"), "attempts": len(tries)})
    return turns, None, turns


# =============================================================================================== 4.-5. audit, memory

def ctx_from_slots(S, N):
    """r3-style situation block (so the r3 audit can be reused unchanged as an independent measurement)."""
    E = {}
    for x in S:
        link = {a: max((N[nd]["link"][a] for nd in x["nodes"] if nd in N), key=["independent", "unverified", "co_generated", "direct_source"].index, default="independent")
                for a in ATTRS}
        E[f"ctx.{x['id']}_{x['key']}"] = {"text": x["say"], "source": "synthetic_task_context", "link": link}
    return {"elements": E, "text": "\n        ".join("- " + e["text"] for e in E.values())}


def build_memory(pr, g, kept, examples):
    pid = pr["persona_id"]
    N = g["nodes"]
    st = Counter()
    turns, order, slots_by_turn = {}, [], {}
    for s in kept:
        for t in s["turns"]:
            turns[t["dia_id"]] = t
            order.append(t["dia_id"])
            slots_by_turn[t["dia_id"]] = [x for x in s["slots"] if x["id"] in t.get("slots", [])]
    n0 = len(P1.LOG[pid])
    with cf.ThreadPoolExecutor(4) as ex:
        rows = [r for rs in ex.map(lambda s: R.extract_session(ARGS, pid, s, examples), kept) for r in rs]
    fmt = Counter(e.get("reason") for e in P1.LOG[pid][n0:] if e["kind"] == "memory_row_dropped")
    st["1_rows_returned_by_extraction"] = len(rows) + sum(fmt.values())
    st["2_rows_passing_format_checks"] = len(rows)

    def sup(job):
        i, it = job
        cl = [(f"{d}/{x['id']}", x) for d in it["dialogue_ids"] for x in slots_by_turn.get(d, [])]
        prompt = T.SUPPORT_PROMPT.format(entry=it["text"], scope=it["scope"], plural="s" if len(it["dialogue_ids"]) > 1 else "",
                                         evidence=R.evidence_text(turns, order, it["dialogue_ids"]),
                                         facts="\n".join(f"- {k}: {x['say']}" for k, x in cl) or "- (none)")
        try:
            out, _ = X.ask(ARGS, [{"role": "user", "content": prompt}], cseed(ARGS, pid, "r4sup", i), pid, f"support_{i + 1:03d}", json_mode=True, temperature=0.0)
            r = as_json(out)
        except Exception:
            r = {}
        keys = {k for k, _ in cl}
        used = [x for k, x in cl if k in (r.get("facts") or []) or k.split("/")[-1] in (r.get("facts") or [])]
        return {"supported": r.get("supported") if r.get("supported") in ("yes", "partly", "no") else "unparsed",
                "scope": r.get("scope") if r.get("scope") in ("one_off", "stable") else it["scope"], "reason": str(r.get("reason", ""))[:240],
                "slots": [{"session": it["sessions"][0], "id": x["id"], "key": x["key"], "say": x["say"], "nodes": x["nodes"]} for x in used]}

    with cf.ThreadPoolExecutor(4) as ex:
        checks = list(ex.map(sup, list(enumerate(rows))))
    qs = Counter()
    items = []
    for it, c in zip(rows, checks):
        qs[c["supported"]] += 1
        if c["supported"] == "no":
            log(pid, "memory_row_dropped", reason="evidence does not support the entry", row=it["text"], why=c["reason"])
            continue
        if c["scope"] != it["scope"]:
            st["scope_corrected"] += 1
        nodes = sorted({nd for x in c["slots"] for nd in x["nodes"]})
        items.append({**it, "scope": c["scope"], "quote_support": c["supported"], "support_reason": c["reason"], "slots": c["slots"], "nodes": nodes,
                      "fact_basis": "registered" if c["slots"] else "unknown",
                      "occurrences": [{"session": it["sessions"][0], "date": it["date"], "dia_id": it["dialogue_ids"][0], "quote": it["quotes"][0], "text": it["text"]}]})
    st["3_rows_after_quote_support_check"] = len(items)

    def fold(a, b, how):
        for k in ("dialogue_ids", "quotes", "sessions", "nodes", "slots", "occurrences"):
            a[k] = a[k] + [x for x in b[k] if k in ("quotes", "occurrences", "slots") or x not in a[k]]
        a["scope"] = "stable" if "stable" in (a["scope"], b["scope"]) else "one_off"
        a["quote_support"] = "partly" if "partly" in (a["quote_support"], b["quote_support"]) else a["quote_support"]
        a["fact_basis"] = "registered" if "registered" in (a["fact_basis"], b["fact_basis"]) else "unknown"
        log(pid, "memory_duplicate_merged", how=how, kept=a["text"], merged=b["text"])

    merged = []
    for it in items:
        w = set(re.findall(r"[a-z0-9']+", it["text"].lower()))
        dup = next((o for o in merged if len(w & o["_w"]) / max(1, len(w | o["_w"])) >= 0.8), None)
        if dup:
            fold(dup, it, "word overlap")
            st["merged_word_overlap"] += 1
        else:
            merged.append({**it, "_w": w})
    for i, o in enumerate(merged, 1):
        o.pop("_w")
        o["memory_id"] = f"x{i:03d}"
    by = {o["memory_id"]: o for o in merged}
    pairs = [(gp[0], o) for gp in R.duplicate_groups(ARGS, pid, merged, "r4") for o in gp[1:]]

    def same(p):
        try:
            out, _ = X.ask(ARGS, [{"role": "user", "content": T3.PAIR_DUPLICATE_PROMPT.format(a=by[p[0]]["text"], b=by[p[1]]["text"])}],
                           cseed(ARGS, pid, "r4pair", *p), pid, f"pair_{p[0]}_{p[1]}", json_mode=True, temperature=0.0)
            return str(as_json(out).get("same", "")).lower() == "yes"
        except Exception:
            return False

    with cf.ThreadPoolExecutor(4) as ex:
        verdicts = list(ex.map(same, pairs))
    gone = set()
    for (a, b), v in zip(pairs, verdicts):
        st["duplicate_pairs_proposed"] += 1
        if v and a not in gone and b not in gone:
            fold(by[a], by[b], "semantic (confirmed pairwise)")
            gone.add(b)
            st["merged_semantic"] += 1
    final = [o for o in merged if o["memory_id"] not in gone]
    for i, o in enumerate(final, 1):
        o["memory_id"] = f"m{i:03d}"
        o["n_sessions"] = len(set(o["sessions"]))
        o["n_occurrences"] = len(o["occurrences"])
    st["4_entries_after_merging_duplicates"] = len(final)

    def ann(it):
        link = {a: max((N[nd]["link"][a] for nd in it["nodes"] if nd in N), key=["independent", "unverified", "co_generated", "direct_source"].index)
                if it["nodes"] else "unknown" for a in ATTRS}
        a = R.annotate(ARGS, pid, it["text"], it["quotes"][0], it["memory_id"], link)
        a["status"] = {f: X.cue_status(a["text_label"][f], link[f], it["fact_basis"]) for f in ATTRS}
        return a

    with cf.ThreadPoolExecutor(4) as ex:
        for it, a in zip(final, ex.map(ann, final)):
            it["annotation"] = a
    age_cue = [it for it in final if it["annotation"]["text_label"]["age"] != "direct"]
    st["5_entries_in_age_cue_only"] = len(age_cue)
    return {"raw": final, "age_cue_only": {"memory": age_cue, "removed": [{"memory_id": it["memory_id"], "text": it["text"]} for it in final if it not in age_cue]},
            "stage_counts": dict(st), "format_drops": dict(fmt), "quote_support_counts": dict(qs)}


# =============================================================================================== validator tests

def validator_tests(profiles, graphs, cats):
    """Known bad messages from r2/r3 must be rejected; known good ones accepted."""
    pr, g = profiles["u007"], graphs["u007"]
    s = {"session_id": "S99", "date": "2026-08-08", "activity": "restaurant_reservation", "errand": "find a place for a weekend lunch and reserve it"}
    S = [slot("s1", "request", s["errand"], "what you want", ["session:S01"], []),
         date_slot("s2", "date", dt.date(2026, 8, 15), "session:S01"),
         slot("s3", "participants", "household family", "who is coming besides you: your wife, your 7-year-old son", ["person:partner", "person:child1"], []),
         slot("s4", "pref_diet", "low-sodium", "your diet: low-sodium", ["pref:diet"], [])]
    user = {"speaker": "User", "slots": ["s1", "s2", "s3", "s4"]}
    asst = {"speaker": "Assistant", "act": "x"}
    cases = [
        (user, "Hi, can you find a lunch place this Saturday, the 15th, for my wife, my 7-year-old son and me? I'm on a low-sodium diet.", False),
        (asst, "I'll look for family-friendly lunch places on Saturday, 8 August.", True),
        (asst, "You could try places like Milwaukee or Wisconsin Dells for a change.", True),
        (user, "I want to stick with low-sodium options, especially for my son, this Saturday the 15th, for my wife, my 7-year-old son and me.", True),
        (user, "Saturday the 15th works since I work in the mornings; it's my wife, my 7-year-old son and me, low-sodium please.", True),
        (user, "Shannon is bringing his wife and 7-year-old son on Saturday the 15th, low-sodium.", True),
        (user, "Do you have any dietary restrictions I should mention for Saturday the 15th with my wife and 7-year-old son? low-sodium", True),
        (asst, "Your order for Saturday, 15 August is all set.", True),
        (user, "Lunch this Saturday, the 15th, for my wife, my 7-year-old son, my mom and me, low-sodium.", True),
        (user, "Lunch this Saturday, the 15th, for my wife, my 7-year-old son and me; low-sodium, and my son is allergic to nuts.", True),
    ]
    res = []
    for msg, text, expect_bad in cases:
        p = check_message(pr, g, cats["u007"], s, S, [], msg, text)
        res.append({"text": text, "expect_rejected": expect_bad, "problems": p, "passed": bool(p) == expect_bad})
    return res


# =============================================================================================== view

def view(pr, g, checks, hist, mem, tasks):
    pid = pr["persona_id"]
    N = g["nodes"]
    V = [f"# {pid} — ProfileFoundry {pr['source']['profile_id']} (r4: fact graph + slot generation)\n",
         f"History: **{hist['status']}** — {len(hist['kept'])} of {hist['planned']} planned sessions realised; {len(hist['failed'])} failed\n",
         "## 1. Fact graph\n", f"{len(N)} nodes, {len(g['edges'])} edges. Graph rules: {sum(c['ok'] for c in checks)}/{len(checks)} pass"
         + ("" if all(c["ok"] for c in checks) else " — FAILED: " + "; ".join(f"{c['rule']} ({c['detail']})" for c in checks if not c["ok"])) + "\n",
         "| node | kind | content | source | link (age / household) |", "|---|---|---|---|---|"]
    for nid, n in N.items():
        if n["kind"] in ("catalog", "session"):
            continue
        content = {k: v for k, v in n.items() if k not in ("id", "kind", "link", "source")}
        V.append(f"| {nid} | {n['kind']} | {json.dumps(content, ensure_ascii=False)[:160]} | {n.get('source')} | {n['link']['age']} / {n['link']['household_children']} |")
    V.append("\nEdges: " + "; ".join(f"{e['from']} —{e['rel']}→ {e['to']}" for e in g["edges"] if e["rel"] != "has_session"))
    V += ["\n## 2. Sessions (slots chosen in code; wording by the model; every message checked by code)\n"]
    for s in hist["kept"]:
        V.append(f"**{s['session_id']} — {dtext(dt.date.fromisoformat(s['date']))} — {s['activity']}** ({s['errand']})")
        V.append("> slots: " + " | ".join(f"{x['id']} {x['say']} [{', '.join(x['nodes'])}]" for x in s["slots"]))
        for t in s["turns"]:
            V.append(f"- `{t['dia_id']}` **{t['speaker']}**" + (f" [{', '.join(t['slots'])}]" if t.get("slots") else "") + f": {t['text']}"
                     + (f" *(worded {t['attempts']}×)*" if t["attempts"] > 1 else ""))
        au = s.get("llm_audit", {})
        flags = [f"{p['type']}: “{p['quote'][:60]}”" for p in au.get("problems", []) if p["source"] != "code"]
        if flags:
            V.append("    - independent LLM audit flags: " + "; ".join(flags))
        V.append("")
    if hist["failed"]:
        V += ["### Sessions that failed (not replaced)\n"]
        for f_ in hist["failed"]:
            last = f_["attempts"][-1]
            V.append(f"- {f_['session_id']} ({f_['activity']}), message {f_['turn']}: last wording “{last['text'][:140]}” — {'; '.join(last['problems'])[:200]}")
    V += ["\n## 3. Memory and its chain (entry → slots of the cited message → graph nodes → attribute status)\n",
          "| id (evidence) | memory | scope ×occ. | quote | graph nodes | age | household | employment | income | education |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    cell = lambda a, f: "" if a["text_label"][f] == "none" and a["status"][f] == "none" else f"{a['text_label'][f]} → {a['status'][f]}"
    for it in mem["raw"]:
        a = it["annotation"]
        V.append(f"| {it['memory_id']} ({','.join(it['dialogue_ids'])}) | {it['text']} | {it['scope']} ×{it['n_occurrences']} | {it['quote_support']} | "
                 f"{', '.join(n for n in it['nodes'] if not n.startswith('session')) or ('session only' if it['nodes'] else 'unknown')} | " + " | ".join(cell(a, f) for f in ATTRS) + " |")
    V += [f"\n## 4. age_cue_only: {len(mem['age_cue_only']['memory'])} entries"
          + (" (identical to section 3)" if not mem["age_cue_only"]["removed"] else f"; removed {mem['age_cue_only']['removed']}"),
          "\n## 5. Current tasks (copied from r2)\n", f"{tasks['city']}; catalog `{tasks['catalog']}`; {tasks['budget_rule']}\n"]
    V += [f"- {t['activity']}: {t['request']} {json.dumps(t['constraints'])}" for t in tasks["tasks"]]
    return "\n".join(V) + "\n"


# =============================================================================================== main

def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--r2", default=os.path.join(ROOT, "data_v2_dialogue_preview_r2"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data_v2_dialogue_preview_r4"))
    ap.add_argument("--input", default=os.path.join(ROOT, "data_v2_preview", "pf", "us_households.jsonl"))
    ap.add_argument("--prev_manifest", default=os.path.join(ROOT, "data_v2_preview", "manifest.json"))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default="qwen3:32b")
    ap.add_argument("--servers", default="http://localhost:11434=1")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--num_ctx", type=int, default=8192)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--only", default="")
    ap.add_argument("--max_sessions", type=int, default=0)
    ap.add_argument("--tests_only", action="store_true")
    ARGS = X.ARGS = args = ap.parse_args()
    P1.POOL = ServerPool(args.servers)
    os.makedirs(args.out, exist_ok=True)
    profiles = {p["persona_id"]: p for p in R.select_profiles(args)}
    cats = {p: json.load(open(os.path.join(args.r2, "catalogs", f"{p}.json"))) for p in profiles}
    H2 = {p: json.load(open(os.path.join(args.r2, "history", f"{p}.json"))) for p in profiles}
    plans = {p: P1.plan_sessions(random.Random(f"{args.seed}-history-{p}")) for p in profiles}     # same plan as r2/r3
    graphs = {p: build_graph(profiles[p], cats[p], H2[p]["standing"], plans[p]) for p in profiles}
    tests = validator_tests(profiles, graphs, cats)
    json.dump(tests, open(os.path.join(args.out, "validator_tests.json"), "w"), indent=2, ensure_ascii=False)
    print(f"validator tests: {sum(t['passed'] for t in tests)}/{len(tests)}")
    for t in tests:
        if not t["passed"]:
            print("  FAIL", t["expect_rejected"], t["text"][:90], t["problems"])
    if args.tests_only or not all(t["passed"] for t in tests):
        return
    examples = X.T2.fact_examples(json.load(open(os.path.join(ROOT, "external", "upstream_templates", "locomo", "fact_generation_examples_new.json"))))
    for sub in ("graph", "history", os.path.join("memory", "raw"), os.path.join("memory", "filtered", "age_cue_only"), "tasks", "view", "personas", "catalogs", "templates"):
        os.makedirs(os.path.join(args.out, sub), exist_ok=True)
    for name in ("USER_REALISE_PROMPT", "ASSISTANT_REALISE_PROMPT", "SUPPORT_PROMPT"):
        open(os.path.join(args.out, "templates", f"r4__{name}.txt"), "w").write(getattr(T, name))
    pids = [p for p in sorted(profiles) if not args.only or p in args.only.split(",")]

    def run(pid):
        pr, g, cat = profiles[pid], graphs[pid], cats[pid]
        plan = plans[pid][:args.max_sessions] if args.max_sessions else plans[pid]
        sessions = []
        for s in plan:
            rng = random.Random(f"{args.seed}-r4slots-{pid}-{s['session_id']}")
            S = build_slots(g, pr, s, rng)
            sessions.append({**s, "slots": S, "plan": make_plan(S, rng)})
        checks = graph_checks(g, sessions)
        kept, failed = [], []

        def one(s):
            turns, bad, partial = realise_session(pr, g, cat, s, s["slots"], s["plan"])
            return s, turns, bad, partial

        with cf.ThreadPoolExecutor(3) as ex:
            for s, turns, bad, partial in ex.map(one, sessions):
                if turns is None:
                    failed.append({"session_id": s["session_id"], "activity": s["activity"], "turn": len(partial) + 1, "attempts": bad, "slots": s["slots"]})
                else:
                    kept.append({**s, "turns": turns})
        # independent measurement with the r3 model checks (not a gate)
        def audit(s):
            d0 = dt.date.fromisoformat(s["date"])
            ctx = ctx_from_slots(s["slots"], g["nodes"])
            pub = R.public_context(pr, d0, R.persona_at(pr, d0)[1])
            res = X.check_v3(pr, s, pub["text"], ctx, f"r4_{s['session_id']}")
            return {k: res[k] for k in ("status", "problems", "claims")}
        with cf.ThreadPoolExecutor(3) as ex:
            for s, a in zip(kept, ex.map(audit, kept)):
                s["llm_audit"] = a
        kept.sort(key=lambda s: s["date"])
        hist = {"persona_id": pid, "planned": len(plan), "kept": kept, "failed": failed,
                "activities_covered": sorted({s["activity"] for s in kept}),
                "status": "ok" if len(kept) >= 12 and len({s["activity"] for s in kept}) == 6 else "failed"}
        mem = build_memory(pr, g, kept, examples)
        tasks = json.load(open(os.path.join(args.r2, "tasks", f"{pid}.json")))
        dump = lambda sub, obj: json.dump(obj, open(os.path.join(args.out, sub, f"{pid}.json"), "w"), indent=2, ensure_ascii=False)
        dump("personas", pr)
        dump("catalogs", cat)
        dump("graph", {**g, "checks": checks})
        dump("history", hist)
        dump("tasks", tasks)
        dump(os.path.join("memory", "raw"), {"persona_id": pid, "memory": mem["raw"], "stage_counts": mem["stage_counts"],
                                             "format_drops": mem["format_drops"], "quote_support_counts": mem["quote_support_counts"]})
        dump(os.path.join("memory", "filtered", "age_cue_only"), {"persona_id": pid, **mem["age_cue_only"]})
        open(os.path.join(args.out, "view", f"{pid}.md"), "w").write(view(pr, g, checks, hist, mem, tasks))
        print(f"{pid}: {hist['status']} realised {len(kept)}/{len(plan)}; graph rules {sum(c['ok'] for c in checks)}/{len(checks)}; memory {mem['stage_counts']}", flush=True)

    with cf.ThreadPoolExecutor(8) as ex:
        list(ex.map(run, pids))
    json.dump(dict(LOG), open(os.path.join(args.out, "generation_log.json"), "w"), indent=2, ensure_ascii=False)
    json.dump(dict(P1.LOG), open(os.path.join(args.out, "failures_and_repairs.json"), "w"), indent=2, ensure_ascii=False)
    json.dump({"version": "r4 (fact graph + slot generation)", "earlier_versions_untouched": ["data_v2_dialogue_preview", "_r2", "_r3"],
               "seed": args.seed, "model": args.model, "new_llm_calls": P1.STATS["llm_calls"],
               "code_sha256": {f: P1.sha(os.path.join(HERE, f)) for f in ("v2r4_preview.py", "v2r4_templates.py", "v2r3_repair.py", "v2r3_templates.py")}},
              open(os.path.join(args.out, "manifest.json"), "w"), indent=2)
    print("done; new LLM calls:", P1.STATS["llm_calls"])


if __name__ == "__main__":
    main()
