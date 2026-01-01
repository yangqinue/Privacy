"""Dataset v2 preview, revision 2: profile -> situation of each errand -> user simulator + separate assistant ->
checks -> extracted memory -> support/trace check -> annotation (text level + generation link) -> tasks.

Revision 1 (scripts/v2_dialogue_preview.py, data_v2_dialogue_preview/) is left unchanged; this script imports its
profile builder and LLM helpers so that the same 8 personas, preferences and session plans are used.

Usage:
  python scripts/v2r2_dialogue_preview.py --out data_v2_dialogue_preview_r2 --seed 0 \
      --servers http://localhost:11436=4,http://localhost:11437=4,http://localhost:11434=1
"""

import argparse
import concurrent.futures as cf
import datetime as dt
import difflib
import inspect
import json
import os
import random
import re
import shutil
import sys
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "pilot"))
import v2_dialogue_preview as P1      # revision 1: profile builder, session plan, LLM call, logging
import v2_templates as T1
import v2r2_templates as T
from run_dev2 import ServerPool

REFERENCE, WINDOW, ERRANDS = P1.REFERENCE, P1.WINDOW, P1.ERRANDS
ATTRS = T.FEATURES
MONTHS = "January February March April May June July August September October November December".split()
WEEKDAYS = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()
log, ask, cseed, as_json, norm = P1.log, P1.ask, P1.cseed, P1.as_json, P1.norm

# synthetic name pools for the local catalogs (fictional; the same pools are used for every city)
POOL = {
    "concert_venues": ["Riverside Hall", "The Lantern Room", "Harbor Street Theater", "Maple Yard Amphitheater", "Copper Line Club",
                       "Old Mill Stage", "Granite Arts Center", "The Blue Door"],
    "restaurants": ["Juniper Table", "Saffron Door", "The Brass Fork", "Alder & Rye", "Blue Kettle Kitchen", "Marigold Diner",
                    "Stone Oven House", "Fennel & Fig"],
    "gyms": ["Northside Fitness Studio", "Summit Climb & Train", "Riverbend Yoga", "Ironworks Gym", "Lakeview Athletic Club",
             "Corner Street Pilates"],
    "grocery_services": ["FreshCart", "GreenBasket", "PantryRun", "DailyCrate"],
    "carriers": ["Northwind Mobile", "Clearwave", "Beacon Wireless", "Tandem Mobile", "Juno Cellular"],
    "destinations": [("Pine Hollow", "lake town"), ("Cedar Ridge", "mountain cabins"), ("Port Alder", "small river town"),
                     ("Stonebridge", "historic small city"), ("Willow Springs", "hot-springs resort area"), ("Elk Meadow", "state park area")],
}
CLASS_TYPES = ["yoga", "spin", "strength training", "pilates", "swimming", "indoor climbing"]
GROCERY_ITEMS = ["rice", "lentils", "spinach", "apples", "potatoes", "carrots", "olive oil", "bananas", "tomatoes", "onions",
                 "black beans", "bell peppers"]
COMPLETION_RE = (r"\b(I(?:'ve| have)(?: just| now| already)? (?:booked|reserved|placed|ordered|purchased|changed|updated|rescheduled|confirmed|scheduled|set up)"
                 r"|(?:has|have) been (?:booked|reserved|placed|ordered|confirmed|changed|updated|rescheduled|scheduled)"
                 r"|(?:is|are) (?:now )?(?:booked|confirmed|reserved)\b|confirmation (?:number|code|email)|you(?:'ll| will) receive a confirmation)")
TRANSACTION_RE = r"\b(confirmation|booking|order|reference) (number|code|id|#)\b|\bconfirmation\b.*\d{4,}"
GROUP_SIZE_RE = (r"\b(?:for|of) (?:two|three|four|five|six|seven|eight|\d+)\b|\b(?:two|three|four|five|six|seven|eight|\d+)"
                 r"[- ](?:tickets?|lines?|people|persons?|travell?ers?|adults?|of us|seats?)\b")


# --------------------------------------------------------------------------------------------- dates (code)

def dtext(d):
    return f"{d.strftime('%A')}, {d.day} {d.strftime('%B')} {d.year}"


def next_weekday(d, names, lo, hi, rng):
    """A date between d+lo and d+hi days whose weekday is in names."""
    c = [d + dt.timedelta(days=k) for k in range(lo, hi + 1) if (d + dt.timedelta(days=k)).strftime("%A") in names]
    return rng.choice(c)


def date_problems(turns, session_date):
    """Weekday/date pairs written in the conversation, checked against the calendar (code, not LLM)."""
    wd = "|".join(f"{x[:3]}(?:{x[3:]})?" for x in WEEKDAYS)
    mo = "|".join(f"{x[:3]}(?:{x[3:]})?" if len(x) > 3 else x for x in MONTHS)
    out = []
    for t in turns:
        found = [(m.group(0), m.group(1), m.group(3), int(m.group(2)), m.group(4))
                 for m in re.finditer(rf"\b({wd})\b\.?,? (?:the )?(\d{{1,2}})(?:st|nd|rd|th)?(?: of)? ({mo})\b\.?(?:,? (\d{{4}}))?", t["text"])]
        found += [(m.group(0), m.group(1), m.group(2), int(m.group(3)), m.group(4))
                  for m in re.finditer(rf"\b({wd})\b\.?,? ({mo})\b\.? (\d{{1,2}})(?:st|nd|rd|th)?\b(?:,? (\d{{4}}))?", t["text"])]
        for raw, w, month, day, year in found:
            # without a year, the date meant is the one from about two months before to a year after the session
            years = [int(year)] if year else [session_date.year - 1, session_date.year, session_date.year + 1]
            cands = []
            for y in years:
                try:
                    c = dt.date(y, [x[:3] for x in MONTHS].index(month[:3]) + 1, day)
                except ValueError:
                    continue
                if year or -60 <= (c - session_date).days <= 305:
                    cands.append(c)
            if not any(c.strftime("%A")[:3] == w[:3] for c in cands):
                out.append({"type": "date_weekday_mismatch", "quote": raw, "source": "code",
                            "reason": f"{raw} is not a {w} ({', '.join(c.isoformat() + ' is a ' + c.strftime('%A') for c in cands) or 'no such date'}); {t['dia_id']}, {t['speaker']}"})
    return out


# ----------------------------------------------------------------------------------------- profile at a date

def rel_label(a, married=True):
    g = a.get("gender")
    table = {"partner": ("husband", "wife") if married else ("partner", "partner"), "parent": ("father", "mother"),
             "adult child": ("son", "daughter"), "sibling": ("brother", "sister")}
    if a["relation"] in table:
        return table[a["relation"]][0 if g == "Male" else 1] if g in ("Male", "Female") else a["relation"]
    return None


def persona_at(pr, d):
    """Readable persona as of date d: age on that date, only events up to that date."""
    f = {k: v["value"] for k, v in pr["fields"].items()}
    iso = d.isoformat()
    later = [e for e in f["life_events"] if e["date"] > iso]
    marital_open = any(e["type"] in ("marriage", "divorce") for e in later)
    job_open = any(e["type"] == "job_change" for e in later)
    move_open = any(e["type"] == "move" for e in later)
    kids = f["own_minor_children"] if isinstance(f["own_minor_children"], list) else []
    married = f["marital_status"] == "Married"
    others = [a for a in f["co_resident_adults"] if a["relation"] != "partner"]
    lines = [
        f"Given name: {f['given_name']}. Age {P1.age_on(f['date_of_birth'], d)} on this date. Gender: {f['gender']}. "
        + ("Home city: not shown for this date." if move_open else f"Lives in {f['city']}."),
        ("Marital status: not shown for this date (do not mention a marital status or a partner)." if marital_open else
         f"Marital status: {f['marital_status']}. Partner living in the same home: "
         + ("yes" if f["partner_at_home"] is True else "no" if f["partner_at_home"] is False else "unknown") + "."),
        "Own children under 18: " + (", ".join(f"{c['age']}-year-old {'son' if c['sex'] == 'boy' else 'daughter'}" for c in kids)
                                     if kids else "none recorded") + ".",
        "Own adult children: " + (", ".join(f"age {c['age']}" + (" (lives at home)" if c["co_resident"] else " (lives elsewhere)")
                                            for c in f["own_adult_children"]) or "none recorded") + ".",
        "Other adults in the home: " + (", ".join((rel_label(a) or "an adult whose relation is not recorded") + f" (age {a['age']})"
                                                  for a in others) or "none") + ".",
        "Employment: " + ("not shown for this date." if job_open else
                          f"{f['employment']['job_title']} at {f['employment']['employer']} (working hours are not recorded)"
                          if f["employment"]["status"] == "Employed"
                          else "unknown (no current job on record; do not state or assume a job, studies or retirement)") + ".",
        "Education: " + (f"{f['education']['degree']} ({f['education']['institution']})" if isinstance(f["education"], dict) else "unknown") + ".",
        "Health: allergies " + (", ".join(f["health"]["allergies"]) or "none recorded")
        + (f"; disability: {f['health']['disability']}" if f["health"]["disability"] else "") + ".",
        "Recorded life events up to this date: " + ("; ".join(f"{e['date'][:7]} {e['text']}" for e in f["life_events"] if e["date"] <= iso) or "none") + ".",
        "Preferences: " + f"{f['preferences']['schedule']}; music: {', '.join(f['preferences']['music'])}; hobbies: "
        f"{', '.join(f['preferences']['hobbies'])}; diet: {f['preferences']['diet']}; {f['preferences']['seating']}.",
    ]
    return "\n        ".join(lines), {"marital_open": marital_open, "job_open": job_open, "move_open": move_open}


def L(**kw):
    """Generation link of a source element to each target attribute (default: independent)."""
    return {a: kw.get(a, "independent") for a in ATTRS}


def profile_elements(pr):
    f = {k: v["value"] for k, v in pr["fields"].items()}
    p = f["preferences"]
    E = {
        "profile.age": ("age / date of birth", L(age="direct_source")),
        "profile.marital_partner": (f"marital status {f['marital_status']}, partner at home: {f['partner_at_home']}",
                                    L(household_children="direct_source", age="unverified")),
        "profile.minor_children": ("own children under 18", L(household_children="direct_source", age="co_generated")),
        "profile.adult_children": ("own adult children", L(household_children="direct_source", age="co_generated")),
        "profile.co_residents": ("other adults in the home (parents, siblings, others)", L(household_children="direct_source", age="unverified")),
        "profile.job": ("job title and employer", L(employment="direct_source", income="unverified", education="unverified", age="unverified")),
        "profile.education": ("degree and institution", L(education="direct_source", age="unverified")),
        "profile.city": (f"home city {f['city']}", L()),
        "profile.health": ("allergies / disability", L(age="unverified")),
        "profile.life_events": ("recorded life events (moves, education, job changes, marriage, divorce)",
                                L(age="co_generated", household_children="unverified", employment="unverified", education="unverified")),
        "pref.schedule": (p["schedule"], L()), "pref.music": ("music: " + ", ".join(p["music"]), L()),
        "pref.hobbies": ("hobbies: " + ", ".join(p["hobbies"]), L()), "pref.diet": ("diet: " + p["diet"], L()),
        "pref.seating": (p["seating"], L()),
    }
    return {k: {"text": t, "source": "synthetic_preference" if k.startswith("pref.") else "profile", "link": l} for k, (t, l) in E.items()}


# --------------------------------------------------------------------------- local catalog and standing facts

def build_catalog(pr, rng):
    city = pr["fields"]["city"]["value"]
    pick = lambda k, n: rng.sample(POOL[k], n)
    oct_days = [dt.date(2026, 10, d) for d in range(2, 32)]
    wk = [d for d in oct_days if d.strftime("%A") in ("Friday", "Saturday", "Sunday")]
    genres = sorted(set(sum((P1.V1.MUSIC,), [])))
    cat = {
        "persona_id": pr["persona_id"], "city": city, "synthetic": True,
        "note": "Synthetic local catalog for this preview: fictional businesses placed in the persona's city. Not real listings.",
        "concerts": [{"id": f"c{i + 1}", "venue": v, "city": city, "genre": rng.choice(genres), "date": (d := rng.choice(wk)).isoformat(),
                      "weekday": d.strftime("%A"), "start": rng.choice(["11:00", "15:00", "19:30", "21:30"]),
                      "price_usd": rng.choice([35, 55, 75, 95, 120])} for i, v in enumerate(pick("concert_venues", 5))],
        "restaurants": [{"id": f"r{i + 1}", "name": v, "city": city, "avg_per_person_usd": rng.choice([18, 28, 40, 55, 75]),
                         "options": rng.sample(["vegetarian", "gluten-free", "low-sodium", "lactose-free", "kids menu", "shellfish-free kitchen"], 3)}
                        for i, v in enumerate(pick("restaurants", 5))],
        "gyms": [{"id": f"g{i + 1}", "name": v, "city": city, "classes": rng.sample(CLASS_TYPES, 3),
                  "ten_class_pack_usd": rng.choice([120, 160, 200, 240, 290])} for i, v in enumerate(pick("gyms", 4))],
        "grocery_services": [{"id": f"s{i + 1}", "name": v, "delivers_in": city, "delivery_fee_usd": rng.choice([0, 4, 6, 9])}
                             for i, v in enumerate(pick("grocery_services", 3))],
        "mobile_plans": [{"id": f"m{i + 1}", "carrier": v, "data": rng.choice(["5 GB", "15 GB", "unlimited"]),
                          "usd_per_line": rng.choice([20, 30, 40, 55])} for i, v in enumerate(pick("carriers", 4))],
        "weekend_destinations": [{"id": f"d{i + 1}", "name": n, "kind": k, "drive_hours_from_city": rng.choice([1.5, 2, 2.5, 3, 4]),
                                  "from": city, "two_nights_per_person_usd": rng.choice([180, 260, 340, 450])}
                                 for i, (n, k) in enumerate(pick("destinations", 4))],
    }
    return cat


def household(pr):
    f = {k: v["value"] for k, v in pr["fields"].items()}
    married = f["marital_status"] == "Married"
    partner = next((rel_label(a, married) for a in f["co_resident_adults"] if a["relation"] == "partner"), None) if f["partner_at_home"] is True else None
    kids = [(f"{c['age']}-year-old {'son' if c['sex'] == 'boy' else 'daughter'}", "minor_child", c["age"])
            for c in (f["own_minor_children"] if isinstance(f["own_minor_children"], list) else [])]
    rel = [(rel_label(a), a["relation"], a["age"]) for a in f["co_resident_adults"] if a["relation"] != "partner" and rel_label(a)]
    return partner, kids, rel, 1 + len(f["co_resident_adults"]) + len(kids)


def member_link(kinds):
    """Generation link of a group of household members to the targets."""
    if not kinds:
        return L()
    age = "co_generated" if any(k in ("minor_child", "adult child") for k in kinds) else "unverified"
    return L(household_children="direct_source", age=age)


def describe(labels):
    labels = ["your " + x for x in labels]
    return "you" + ("" if not labels else " and " + labels[0] if len(labels) == 1 else ", " + ", ".join(labels[:-1]) + " and " + labels[-1])


def build_standing(pr, cat, rng):
    """Errand details that stay the same across the year (synthetic; fixed per persona before any conversation)."""
    partner, kids, rel, n_home = household(pr)
    line_opts = [("only you", [], 1)]
    if partner:
        line_opts.append((describe([partner]), ["partner"], 2))
    fam = ([(partner, "partner", None)] if partner else []) + [k for k in kids if k[2] >= 12] + rel
    if len(fam) >= 2 or (fam and not partner):
        line_opts.append((describe([x[0] for x in fam]), [x[1] for x in fam], 1 + len(fam)))
    who, kinds, n = rng.choice(line_opts)
    plan = rng.choice(["5 GB", "10 GB", "15 GB", "unlimited"])
    return {"source": "synthetic_task_context", "carrier": rng.choice(cat["mobile_plans"])["carrier"], "plan_data": plan,
            "monthly_use_gb": rng.choice([3, 6, 9, 14, 22]), "lines": n, "lines_who": who, "lines_kinds": kinds,
            "monthly_bill_usd": 35 + 25 * n + rng.choice([0, 5, 10, 15]),
            "grocery_service": rng.choice(cat["grocery_services"])["name"], "usual_items": rng.sample(GROCERY_ITEMS, 5),
            "household_size": n_home, "household_kinds": (["partner"] if partner else []) + [x[1] for x in kids + rel]}


# ------------------------------------------------------------------------------------- situation of an errand

def companions(pr, rng, allow_family=True):
    """Who comes along. Uniform over the relation types that exist for this person; the rule never looks at age."""
    partner, kids, rel, _ = household(pr)
    opts = [("alone", [], []), ("friend", ["a friend"], [])]
    if partner:
        opts.append(("partner", [partner], ["partner"]))
    if allow_family and (kids or rel):
        fam = ([(partner, "partner", None)] if partner else []) + kids + rel
        opts.append(("household family", [x[0] for x in fam], [x[1] for x in fam]))
    kind, labels, kinds = rng.choice(opts)
    if kind == "alone":
        text = "you go alone (1 person)"
    elif kind == "friend":
        text = "you and a friend (2 people)"
    else:
        text = f"{describe(labels)} ({1 + len(labels)} people)"
    return {"kind": kind, "members": labels, "n": 1 + len(labels), "text": text, "link": member_link(kinds)}


def build_context(pr, s, standing, cat, rng):
    """Structured situation of one session, fixed before the conversation. All details are synthetic and sampled
    without looking at age; participants come from relations that exist in the profile."""
    d0 = dt.date.fromisoformat(s["date"])
    act, k = s["activity"], ERRANDS[s["activity"]].index(s["errand"])
    E = {}

    def el(key, text, link=None):
        E["ctx." + key] = {"text": text, "source": "synthetic_task_context", "link": link or L()}

    part = None
    if act == "concert_ticket_booking":
        part = companions(pr, rng)
        day = next_weekday(d0, ("Friday", "Saturday", "Sunday"), 3, 16, rng)
        if k == 2:
            venue = rng.choice(cat["concerts"])["venue"]
            new = next_weekday(day, ("Friday", "Saturday", "Sunday"), 5, 16, rng)
            el("existing_booking", f"you are holding {part['n']} seat(s) for a show at {venue} on {dtext(day)} (not paid yet)")
            el("change_wanted", rng.choice([f"you would rather go on {dtext(new)}", "you would like seats closer to the aisle or a different section"]))
        else:
            el("when", f"you are looking at shows on {dtext(day)}" + (" or that same weekend" if k == 0 else ""))
            el("tickets", f"{part['n']} ticket(s) needed")
    elif act == "restaurant_reservation":
        part = companions(pr, rng)
        place = rng.choice(cat["restaurants"])["name"]
        if k == 0:
            day = d0 + dt.timedelta(days=rng.randint(1, 8))
            el("when", f"dinner on {dtext(day)} at about {rng.choice(['6:00 pm', '6:30 pm', '7:00 pm', '7:30 pm', '8:00 pm', '8:30 pm'])}")
            el("place", rng.choice([f"you have {place} in mind", "no place chosen yet"]))
        elif k == 1:
            day = next_weekday(d0, ("Saturday", "Sunday"), 1, 8, rng)
            el("when", f"lunch on {dtext(day)} at about {rng.choice(['11:30 am', '12:00 pm', '12:30 pm', '1:00 pm', '1:30 pm'])}")
            el("place", "no place chosen yet")
        else:
            day = d0 + dt.timedelta(days=rng.randint(0, 5))
            old, new = rng.sample(["6:00 pm", "6:30 pm", "7:00 pm", "7:30 pm", "8:00 pm", "8:30 pm", "9:00 pm"], 2)
            el("existing_booking", f"you have a dinner reservation at {place} on {dtext(day)} at {old}")
            el("change_wanted", f"you want to move it to {new} the same day")
    elif act == "fitness_class_booking":
        part = companions(pr, rng, allow_family=False)
        gym = rng.choice(cat["gyms"])
        el("class", f"class type you want to try: {rng.choice(gym['classes'])}")
        el("place", f"gym you are looking at: {gym['name']}" if k == 0 else "no gym chosen yet")
        el("days", f"days that suit you this time: {' and '.join(rng.sample(WEEKDAYS, 2))}")
        if k == 1:
            el("when", f"you would like the trial session in the week starting {dtext(next_weekday(d0, ('Monday',), 1, 8, rng))}")
    elif act == "weekend_trip_booking":
        part = companions(pr, rng)
        fri = next_weekday(d0, ("Friday",), 7, 30, rng)
        dest = rng.choice(cat["weekend_destinations"])
        el("when", f"two nights, from {dtext(fri)} to {dtext(fri + dt.timedelta(days=2))}")
        el("destination", (f"you are thinking of {dest['name']} ({dest['kind']}, about {dest['drive_hours_from_city']} hours' drive)"
                           if rng.random() < 0.7 else "no destination chosen yet; within about 3 hours' drive"))
        el("transport", rng.choice(["you would drive", "you would rather take a train or bus", "no preference on transport"]))
        if k == 0:
            el("lodging", f"kind of place to stay: {rng.choice(['hotel', 'cabin', 'vacation rental', 'no preference'])}")
    elif act == "grocery_delivery":
        day = d0 + dt.timedelta(days=rng.randint(1, 4))
        el("service", f"grocery service you use: {standing['grocery_service']}")
        el("when", f"delivery wanted on {dtext(day)}, {rng.choice(['morning', 'afternoon', 'evening'])} slot")
        el("household", f"the order is for the home ({standing['household_size']} people live there)",
           member_link(standing["household_kinds"] or ["other"]) if standing["household_size"] > 1 else L())
        if k == 1:
            el("items", "your usual order: " + ", ".join(standing["usual_items"]))
        elif k == 2:
            el("items", "items to add for the meal: " + ", ".join(rng.sample(GROCERY_ITEMS, 4)))
    else:
        el("carrier", f"current carrier: {standing['carrier']}; current plan: {standing['plan_data']} of data")
        el("usage", f"you use about {standing['monthly_use_gb']} GB a month; the bill is about ${standing['monthly_bill_usd']} a month")
        el("lines", f"lines on the plan: {standing['lines']} ({standing['lines_who']})", member_link(standing["lines_kinds"]))
        el("reason", rng.choice(["the bill went up recently", "you want more data", "calls drop at home sometimes", "you just want to pay less"]))
    if part:
        el("participants", "who is coming: " + part["text"], part["link"])
    return {"source": "synthetic_task_context", "session_id": s["session_id"], "activity": act, "errand": s["errand"],
            "participants": part and {k2: part[k2] for k2 in ("kind", "members", "n")}, "elements": E,
            "text": "\n        ".join("- " + e["text"] for e in E.values())}


def public_context(pr, d, flags):
    cal = [d + dt.timedelta(days=i) for i in range(35)]
    rows = [", ".join(f"{x.strftime('%a')} {x.day} {x.strftime('%b')}" for x in cal[i:i + 7]) for i in range(0, 35, 7)]
    city = pr["fields"]["city"]["value"]
    lines = [f"- Today is {dtext(d)}."]
    if not flags["move_open"]:
        lines.append(f"- The user's home city in the account settings: {city}.")
    lines.append(f"- Calendar of the coming weeks ({cal[0].year}" + (f"/{cal[-1].year}" if cal[-1].year != cal[0].year else "") + "): " + "; ".join(rows) + ".")
    return {"provided": ["today's date and weekday", "calendar of the next 35 days"] + ([] if flags["move_open"] else ["home city (account setting)"]),
            "not_provided": ["profile", "situation of the errand", "earlier conversations", "memory"], "text": "\n".join(lines)}


# ------------------------------------------------------------------------------------------- history sessions

def clean(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    text = re.sub(r"^(User|Assistant|Chatbot)\s*:\s*", "", text, flags=re.I).strip()
    return text.strip('"“” \n')


def simulate(args, pr, s, ctx, pub, persona, attempt):
    pid, sid = pr["persona_id"], s["session_id"]
    tag = f"{sid}" + (f"_regen{attempt}" if attempt else "")
    sys_u = T.user_simulator_prompt(persona, P1.preference_text(pr, s["activity"]), ctx["text"], s["date_text"], s["errand"])
    sys_a = T.HISTORY_ASSISTANT_PROMPT.format(public_context=pub["text"])
    n_user = 2 + cseed(args, pid, "turns", sid, attempt) % 2
    conv = []
    for i in range(n_user):
        mu = [{"role": "system", "content": sys_u}, {"role": "user", "content": "(The conversation starts. Write the first user message.)"}]
        for t in conv:
            mu.append({"role": "assistant" if t["role"] == "user" else "user", "content": t["content"]})
        if i == n_user - 1 and i > 0:
            mu[-1]["content"] += "\n(This is your last message in this conversation.)"
        for speaker, msgs in (("user", mu), ("assistant", None)):
            if speaker == "assistant":
                msgs = [{"role": "system", "content": sys_a}] + [{"role": t["role"], "content": t["content"]} for t in conv]
            text = ""
            for r in range(3):
                out, _ = ask(args, msgs, cseed(args, pid, "sim", sid, attempt, len(conv), r), pid, f"sim_{tag}_{len(conv) + 1}_{speaker}")
                text = clean(out)
                if text:
                    break
            if not text:
                log(pid, "simulation_failed", session=sid, turn=len(conv) + 1, speaker=speaker)
                return None
            conv.append({"role": speaker, "content": text})
    n = int(sid[1:])
    turns = [{"dia_id": f"D{n}:{i + 1}", "speaker": "User" if t["role"] == "user" else "Assistant", "text": t["content"]} for i, t in enumerate(conv)]
    return {**s, "context": ctx, "assistant_public_context": {k: pub[k] for k in ("provided", "not_provided")}, "turns": turns, "regenerated": attempt}


def check_session(args, pr, s, persona, situation, pub_text, tag=None):
    """Code checks (dates, completion claims) plus one LLM check against profile and situation."""
    pid = pr["persona_id"]
    d = dt.date.fromisoformat(s["date"])
    probs = date_problems(s["turns"], d)
    for t in s["turns"]:
        m = re.search(COMPLETION_RE, t["text"], re.I) if t["speaker"] == "Assistant" else None
        if m:
            probs.append({"type": "assistant_claims_completion", "quote": m.group(0), "source": "code",
                          "reason": f"the assistant has no tools but says this in {t['dia_id']}"})
    conv = "\n".join(f"{t['speaker']}: {t['text']}" for t in s["turns"])
    prompt = T.SESSION_CHECK_PROMPT.format(profile=persona, situation=situation, public_context=pub_text, date=dtext(d), conversation=conv)
    try:
        text, _ = ask(args, [{"role": "user", "content": prompt}], cseed(args, pid, "check", s["session_id"], s.get("regenerated", 0)),
                      pid, tag or f"check_{s['session_id']}_{s.get('regenerated', 0)}", think=True, temperature=0.0)
        for p in as_json(text).get("problems", []):
            if isinstance(p, dict) and p.get("type") and not (p["type"] == "assistant_claims_completion"
                                                              and any(q["type"] == p["type"] for q in probs)):
                probs.append({**p, "source": "llm"})
    except Exception as e:
        log(pid, "session_check_error", session=s["session_id"], error=str(e))
        return {"status": "check_failed", "problems": probs}
    return {"status": "ok" if not probs else "not_ok", "problems": probs}


def cross_check(args, pr, standing, sessions):
    pid = pr["persona_id"]
    block = "\n\n".join(f"[{s['session_id']}] {dtext(dt.date.fromisoformat(s['date']))}\n" + "\n".join("- " + t["text"] for t in s["turns"] if t["speaker"] == "User")
                        for s in sessions)
    prof = persona_at(pr, REFERENCE)[0] + "\n        Standing details: " + json.dumps({k: v for k, v in standing.items() if k not in ("source", "lines_kinds", "household_kinds")})
    try:
        text, _ = ask(args, [{"role": "user", "content": T.CROSS_SESSION_PROMPT.format(profile=prof, sessions=block)}],
                      cseed(args, pid, "cross"), pid, "cross_session_check", think=True, temperature=0.0)
        ids = {s["session_id"] for s in sessions}
        return [c for c in as_json(text).get("conflicts", []) if isinstance(c, dict) and set(c.get("session_ids", [])) <= ids
                and len(c.get("session_ids", [])) >= 2]
    except Exception as e:
        log(pid, "cross_check_error", error=str(e))
        return []


def build_history(args, pr, cat, standing, rng):
    pid = pr["persona_id"]
    plan = P1.plan_sessions(rng)            # same plan as revision 1 (same RNG stream)
    kept, dropped, first_pass = [], [], {}

    def run(s, attempt):
        d = dt.date.fromisoformat(s["date"])
        persona, flags = persona_at(pr, d)
        ctx = build_context(pr, s, standing, cat, random.Random(f"{args.seed}-ctx-{pid}-{s['session_id']}-{attempt}"))
        pub = public_context(pr, d, flags)
        g = simulate(args, pr, s, ctx, pub, persona, attempt)
        if g is None:
            return {**s, "context": ctx, "turns": [], "regenerated": attempt}, {"status": "generation_failed", "problems": []}
        return g, check_session(args, pr, g, persona, ctx["text"], pub["text"])

    def place(g, c):
        if c["status"] == "ok":
            kept.append({**g, "check": c})
        else:
            dropped.append({**g, "check": c})
            log(pid, "session_dropped", session=g["session_id"], attempt=g["regenerated"], status=c["status"],
                problems=[f"{p.get('type')} [{p.get('source')}]: {p.get('reason')}" for p in c["problems"]])

    with cf.ThreadPoolExecutor(3) as ex:
        for g, c in ex.map(lambda s: run(s, 0), plan):
            first_pass[g["session_id"]] = c["status"]
            place(g, c)
    kept.sort(key=lambda s: s["date"])
    conflicts = cross_check(args, pr, standing, kept) if kept else []
    for c in conflicts:
        victim = sorted(c["session_ids"])[-1]
        hit = [s for s in kept if s["session_id"] == victim]
        if hit:
            kept.remove(hit[0])
            dropped.append({**hit[0], "check": {"status": "cross_session_conflict", "problems": [{"type": "cross_session_conflict", "source": "llm", **c}]}})
            log(pid, "session_dropped", session=victim, status="cross_session_conflict", problems=[c.get("reason")])
    # one repair round, only when the persona would otherwise fail; sessions of a missing activity first
    missing = set(ERRANDS) - {s["activity"] for s in kept}
    if len(kept) < 12 or missing:
        todo = sorted(dropped, key=lambda s: (s["activity"] not in missing, s["session_id"]))
        for dsess in todo:
            missing = set(ERRANDS) - {s["activity"] for s in kept}
            if len(kept) >= 12 and not missing:
                break
            if len(kept) >= 12 and dsess["activity"] not in missing:
                continue
            base = {k: dsess[k] for k in ("session_id", "date", "date_text", "activity", "errand")}
            g, c = run(base, 1)
            log(pid, "session_regenerated" if c["status"] == "ok" else "session_regeneration_failed", session=base["session_id"], status=c["status"])
            if c["status"] == "ok":
                kept.append({**g, "check": c})
            else:
                dropped.append({**g, "check": c})
    kept.sort(key=lambda s: s["date"])
    return {"persona_id": pid, "planned": len(plan), "first_pass": first_pass, "kept": kept, "dropped": dropped,
            "cross_session_conflicts": conflicts,
            "dates_in_window": all(WINDOW[0].isoformat() <= s["date"] <= WINDOW[1].isoformat() for s in kept),
            "activities_covered": sorted({s["activity"] for s in kept}),
            "status": "ok" if len(kept) >= 12 and len({s["activity"] for s in kept}) == 6 else "failed"}


# ---------------------------------------------------------------------------------------------------- memory

def extract_session(args, pid, s, examples):
    messages = [{"role": "system", "content": T.CONVERSATION2FACTS_PROMPT}]
    for inp, out in examples:
        messages += [{"role": "user", "content": inp}, {"role": "assistant", "content": out}]
    messages.append({"role": "user", "content": "CONVERSATION: " + T.render_conversation(s)})
    try:
        text, _ = ask(args, messages, cseed(args, pid, "facts", s["session_id"]), pid, f"facts_{s['session_id']}", json_mode=True, temperature=0.0)
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
        if re.search(TRANSACTION_RE, fact, re.I):
            log(pid, "memory_row_dropped", session=s["session_id"], reason="transaction result (confirmation/order number)", row=fact)
            continue
        out.append({"text": fact, "dialogue_ids": [did], "quotes": [quote], "sessions": [s["session_id"]], "date": s["date"],
                    "subject": subject if subject in ("self", "third_party") else "self",
                    "scope": scope if scope in ("one_off", "stable") else "one_off"})
    return out


def evidence_text(turns_by_id, order, ids):
    out = []
    for did in ids:
        i = order.index(did)
        if i > 0:
            p = turns_by_id[order[i - 1]]
            out.append(f"[{p['dia_id']}] {p['speaker']}: {p['text']}")
        out.append(f"[{did}] User: {turns_by_id[did]['text']}")
    return "\n".join(out)


def support_check(args, pid, it, evidence, elements, tag):
    """Does the cited evidence support the entry, is the scope right, and which source elements does it reflect?"""
    el = "\n".join(f"- {k}: {v['text']}" for k, v in elements.items())
    prompt = T.SUPPORT_PROMPT.format(entry=it["text"], scope=it["scope"], plural="s" if len(it["dialogue_ids"]) > 1 else "",
                                     evidence=evidence, elements=el)
    try:
        text, _ = ask(args, [{"role": "user", "content": prompt}], cseed(args, pid, "support", tag), pid, f"support_{tag}", json_mode=True, temperature=0.0)
        r = as_json(text)
        return {"supported": r.get("supported") if r.get("supported") in ("yes", "partly", "no") else "unparsed",
                "scope": r.get("scope") if r.get("scope") in ("one_off", "stable") else it["scope"],
                "elements": [e for e in r.get("elements", []) if e in elements], "reason": str(r.get("reason", ""))[:300]}
    except Exception as e:
        log(pid, "support_check_error", item=tag, error=str(e))
        return {"supported": "unparsed", "scope": it["scope"], "elements": [], "reason": "check failed"}


def merge_into(a, b):
    for k in ("dialogue_ids", "quotes", "sessions", "elements"):
        a[k] += [x for x in b[k] if x not in a[k] or k == "quotes"]
    a["scope"] = "stable" if "stable" in (a["scope"], b["scope"]) else "one_off"
    a["support"] = "partly" if "partly" in (a["support"], b["support"]) else a["support"]
    a.setdefault("merged_texts", []).append(b["text"])


def duplicate_groups(args, pid, items, tag):
    if len(items) < 2:
        return []
    listing = "\n".join(f"{it['memory_id']}: {it['text']}" for it in items)
    try:
        text, _ = ask(args, [{"role": "user", "content": T.DUPLICATE_PROMPT.format(items=listing)}], cseed(args, pid, "dup", tag), pid, f"duplicates_{tag}",
                      json_mode=True, temperature=0.0)
        ids, seen, out = {it["memory_id"] for it in items}, set(), []
        for g in as_json(text).get("groups", []):
            g = [x for x in dict.fromkeys(g) if x in ids and x not in seen] if isinstance(g, list) else []
            if len(g) >= 2:
                out.append(g)
                seen.update(g)
        return out
    except Exception as e:
        log(pid, "duplicate_check_error", error=str(e))
        return []


def link_of(elements, ids):
    rank = ["independent", "unverified", "co_generated", "direct_source"]
    if not ids:
        return {a: "untraced" for a in ATTRS}
    return {a: max((elements[i]["link"][a] for i in ids), key=rank.index) for a in ATTRS}


def cue_status(label, link):
    if label in ("direct", "indirect"):
        return {"direct_source": "verified_cue", "co_generated": "verified_cue", "independent": "unsupported_association"}.get(link, "unverified")
    if label == "uncertain":
        return "uncertain"
    return "linked_not_apparent" if link in ("direct_source", "co_generated") else "none"


def annotate(args, pid, text, quote, tag, link):
    """Two records per attribute: text_label (what the text states or suggests; SynthPAI template) and
    generation_link (how the source of this item relates to the attribute in our generation process; code)."""
    try:
        out, _ = ask(args, [{"role": "user", "content": T.build_tagging_memory_prompt(text, quote)}], cseed(args, pid, "tag", tag), pid, f"tag_{tag}", temperature=0.0)
        a = T.parse_tagging(out)
    except Exception as e:
        log(pid, "annotation_error", item=tag, error=str(e))
        a = {"labels": {f: "uncertain" for f in ATTRS}, "certainty": None, "reasoning": "annotation failed"}
    return {"text_label": a["labels"], "generation_link": link, "status": {f: cue_status(a["labels"][f], link[f]) for f in ATTRS},
            "certainty": a["certainty"], "reasoning": a["reasoning"], "group_size_cue": bool(re.search(GROUP_SIZE_RE, text, re.I)),
            "regex_review": [f for f, pat in P1.REVIEW_REGEX.items() if re.search(pat, text, re.I) and a["labels"][f] in ("none", "uncertain")]}


def build_memory(args, pr, history, examples):
    pid = pr["persona_id"]
    pel = profile_elements(pr)
    rows, turns, order, sess_el = [], {}, [], {}
    for s in history["kept"]:
        for t in s["turns"]:
            turns[t["dia_id"]] = t
            order.append(t["dia_id"])
        sess_el[s["session_id"]] = {**s["context"]["elements"], **pel}
    with cf.ThreadPoolExecutor(3) as ex:
        for r in ex.map(lambda s: extract_session(args, pid, s, examples), history["kept"]):
            rows += r
    for i, it in enumerate(rows):
        it["_tag"] = f"r{i + 1:03d}"

    def sup(it):
        return support_check(args, pid, it, evidence_text(turns, order, it["dialogue_ids"]), sess_el[it["sessions"][0]], it["_tag"])

    with cf.ThreadPoolExecutor(3) as ex:
        checks = list(ex.map(sup, rows))
    counts = {"extracted": len(rows), "yes": 0, "partly": 0, "no": 0, "unparsed": 0, "scope_changed": 0}
    items, all_el = [], {}
    for it, c in zip(rows, checks):
        counts[c["supported"]] += 1
        if c["supported"] == "no":
            log(pid, "memory_row_dropped", reason="evidence does not support the entry", row=it["text"], evidence=it["quotes"][0], why=c["reason"])
            continue
        if c["scope"] != it["scope"]:
            counts["scope_changed"] += 1
            log(pid, "memory_scope_corrected", row=it["text"], was=it["scope"], now=c["scope"], why=c["reason"])
        sid = it["sessions"][0]
        els = [f"{sid}/{e}" if e.startswith("ctx.") else e for e in c["elements"]]
        for e, full in zip(c["elements"], els):
            all_el[full] = sess_el[sid][e]
        items.append({**{k: v for k, v in it.items() if k != "_tag"}, "scope": c["scope"], "support": c["supported"],
                      "support_reason": c["reason"], "elements": els})
    # duplicates: word overlap first, then one semantic pass; every merge keeps all evidence ids
    merged = []
    for it in items:
        w = set(re.findall(r"[a-z0-9']+", it["text"].lower()))
        dup = next((o for o in merged if len(w & o["_w"]) / max(1, len(w | o["_w"])) >= 0.8), None)
        if dup:
            merge_into(dup, it)
            log(pid, "memory_duplicate_merged", how="word overlap", kept=dup["text"], merged=it["text"])
        else:
            merged.append({**it, "_w": w})
    for i, o in enumerate(merged, 1):
        o.pop("_w")
        o["memory_id"] = f"x{i:03d}"
    by = {o["memory_id"]: o for o in merged}
    gone = set()
    stop = set("user users user's wants want is are to a an the for of and or in on at with their they this that be has have would like looking "
               "prefers prefer requested asked needs need interested".split())
    cw = lambda t: set(re.findall(r"[a-z0-9']+", t.lower())) - stop
    for g in duplicate_groups(args, pid, merged, "pass1"):
        for other in g[1:]:
            a, b = cw(by[g[0]]["text"]), cw(by[other]["text"])
            if len(a & b) / max(1, len(a | b)) < 0.25:   # guard against merging entries that only share a topic
                log(pid, "memory_merge_rejected", kept=by[g[0]]["text"], not_merged=by[other]["text"], reason="proposed as duplicate but content words differ")
                continue
            merge_into(by[g[0]], by[other])
            gone.add(other)
            log(pid, "memory_duplicate_merged", how="semantic", kept=by[g[0]]["text"], merged=by[other]["text"])
    final = [o for o in merged if o["memory_id"] not in gone]
    for i, o in enumerate(final, 1):
        o["memory_id"] = f"m{i:03d}"
        o["n_sessions"] = len(set(o["sessions"]))
    residual = duplicate_groups(args, pid, final, "residual")

    def ann(it):
        return annotate(args, pid, it["text"], it["quotes"][0], it["memory_id"], link_of(all_el, it["elements"]))

    with cf.ThreadPoolExecutor(3) as ex:
        for it, a in zip(final, ex.map(ann, final)):
            it["annotation"] = a
    age_cue, removed = [], []
    for it in final:
        if it["annotation"]["text_label"]["age"] != "direct":
            age_cue.append(it)
            continue
        src = " ".join(it["quotes"])
        atoms = []
        try:
            text, _ = ask(args, [{"role": "user", "content": T.SPLIT_PROMPT.format(entry=it["text"], quote=src)}],
                          cseed(args, pid, "split", it["memory_id"]), pid, f"split_{it['memory_id']}", json_mode=True, temperature=0.0)
            for k, f in enumerate(as_json(text).get("facts", []), 1):
                if isinstance(f, dict) and f.get("text") and len(norm(f.get("quote", ""))) >= 3 and norm(f["quote"]) in norm(src):
                    aid = f"{it['memory_id']}.{k}"
                    atoms.append({**{k2: it[k2] for k2 in ("dialogue_ids", "sessions", "subject", "scope", "elements", "support")},
                                  "memory_id": aid, "parent": it["memory_id"], "text": f["text"], "quotes": [f["quote"]],
                                  "annotation": annotate(args, pid, f["text"], f["quote"], aid, it["annotation"]["generation_link"])})
                else:
                    log(pid, "atom_dropped", item=it["memory_id"], reason="no verbatim quote of its own", atom=str(f)[:160])
        except Exception as e:
            log(pid, "split_error", item=it["memory_id"], error=str(e))
        keep = [a for a in atoms if a["annotation"]["text_label"]["age"] != "direct"]
        drop = [a for a in atoms if a["annotation"]["text_label"]["age"] == "direct"]
        age_cue += keep
        removed.append({"memory_id": it["memory_id"], "text": it["text"],
                        "reason": "direct age statement" + ("" if atoms else " (could not be split; whole item removed)"),
                        "atoms_kept": [a["text"] for a in keep], "atoms_removed": [a["text"] for a in drop]})
        log(pid, "age_direct_item_split", item=it["memory_id"], kept=len(keep), removed=len(drop))
    filtered = {"age_cue_only": {"memory": age_cue, "removed": removed}}
    return {"raw": final, "filtered": filtered, "support_counts": counts, "residual_duplicate_groups": residual,
            "source_elements": all_el}


# ----------------------------------------------------------------------------------------------------- tasks

def build_tasks(args, pr, cat, rng):
    """Current tasks: same rules and RNG stream as revision 1, now tied to the persona's local catalog."""
    pid = pr["persona_id"]
    f = {k: v["value"] for k, v in pr["fields"].items()}
    partner = f["partner_at_home"] is True
    minors = f["own_minor_children"] if isinstance(f["own_minor_children"], list) else []
    others = [a for a in f["co_resident_adults"] if a["relation"] != "partner"]
    bracket = pr["income_bracket_for_scoring"]
    lo, hi = P1.BUDGET_RANGE[bracket] if bracket else P1.BUDGET_COMMON
    budget = lambda base: int(round(base * rng.uniform(lo, hi) / 10) * 10)
    diners = 1 + int(partner) + len(minors) + sum(1 for _ in others if rng.random() < 0.5)
    travelers = 1 + int(partner) + len(minors)
    lines = 1 + int(partner) + sum(1 for c in minors if c["age"] >= 12)
    home = 1 + len(f["co_resident_adults"]) + len(minors)
    sat, fri, sun = dt.date(2026, 10, 3), dt.date(2026, 10, 23), dt.date(2026, 10, 25)
    assert (sat.strftime("%A"), fri.strftime("%A"), sun.strftime("%A")) == ("Saturday", "Friday", "Sunday")
    inc = "direct_source" if bracket else "independent"
    hh = lambda n, kids: L(income=inc, household_children="direct_source" if n > 1 else "independent",
                           age="co_generated" if kids else "unverified" if n > 1 else "independent")
    raw = [
        ("concert_ticket_booking", "concerts", "Please buy two tickets for a weekend show.",
         {"date_window": ["2026-10-10", "2026-10-25"], "num_tickets": 2, "total_budget_usd": budget(180)},
         "two tickets for every persona (constant)", L(income=inc)),
        ("restaurant_reservation", "restaurants", f"Please book a dinner for {max(diners, 2)} on Saturday, October 3.",
         {"date": sat.isoformat(), "weekday": "Saturday", "party_size": max(diners, 2), "total_budget_usd": budget(45 * max(diners, 2))},
         "persona + partner at home + own minor children + co-resident adults who join (each with probability 0.5); minimum 2",
         hh(diners, minors)),
        ("fitness_class_booking", "gyms", "Please find and book a 10-class pack at a gym near me.", {"total_budget_usd": budget(220)},
         "persona only", L(income=inc)),
        ("weekend_trip_booking", "weekend_destinations",
         f"Please plan and book a two-night trip for {travelers} from Friday, October 23 to Sunday, October 25.",
         {"date_window": [fri.isoformat(), sun.isoformat()], "nights": 2, "travelers": travelers, "total_budget_usd": budget(350 + 150 * travelers)},
         "persona + partner at home + own minor children", hh(travelers, minors)),
        ("grocery_delivery", "grocery_services", "Please set up this week's grocery delivery.",
         {"household_size": home, "total_budget_usd": budget(60 + 40 * home)}, "everyone living in the home", hh(home, minors)),
        ("mobile_plan_purchase", "mobile_plans", f"Please find a better mobile plan with {lines} line(s).",
         {"lines": lines, "max_monthly_usd": budget(40 + 35 * lines)}, "persona + partner at home + own children aged 12 or older",
         hh(lines, [c for c in minors if c["age"] >= 12])),
    ]
    tasks = []
    for k, (act, key, req, cons, rule, link) in enumerate(raw, 1):
        tasks.append({"task_id": f"{pid}_t{k:02d}", "activity": act, "city": f["city"], "catalog": f"catalogs/{pid}.json#{key}",
                      "request": req, "constraints": cons, "participants_rule": rule,
                      "self_leak": annotate(args, pid, req + " Constraints: " + json.dumps(cons), req, f"task{k:02d}", link)})
    return {"persona_id": pid, "city": f["city"], "catalog": f"catalogs/{pid}.json",
            "budget_rule": (f"multiplier ~ U{P1.BUDGET_RANGE[bracket]} for household income {bracket}" if bracket
                            else f"multiplier ~ U{P1.BUDGET_COMMON}: household income incomplete, income-independent common range"),
            "tasks": tasks}


# ------------------------------------------------------------------------------------------------------ views

def view(pr, cat, standing, hist, mem, tasks):
    pid = pr["persona_id"]
    V = [f"# {pid} — ProfileFoundry {pr['source']['profile_id']} (revision 2)\n",
         f"History status: **{hist['status']}** ({len(hist['kept'])} sessions kept of {hist['planned']} planned; {len(hist['dropped'])} dropped)\n",
         "## 1. Profile with provenance\n", "| field | value | source | basis |", "|---|---|---|---|"]
    for k, v in pr["fields"].items():
        V.append(f"| {k} | {json.dumps(v['value'], ensure_ascii=False)} | {v['source']} | {v['basis']} |")
    V += ["\n## 2. Standing errand details and local catalog (synthetic)\n",
          "Standing details (fixed for the year): " + json.dumps({k: v for k, v in standing.items() if k not in ('source', 'lines_kinds', 'household_kinds')}),
          f"\nLocal catalog: `catalogs/{pid}.json` — fictional businesses in {cat['city']}: "
          + "; ".join(f"{k}: " + ", ".join(str(x.get('name') or x.get('venue') or x.get('carrier')) for x in cat[k])
                      for k in ("concerts", "restaurants", "gyms", "grocery_services", "mobile_plans", "weekend_destinations")),
          "\n## 3. History sessions kept\n",
          "The assistant was given: today's date and weekday, a calendar, and the home city (account setting). It did not see the profile or the situation.\n"]
    for s in hist["kept"]:
        V.append(f"**{s['session_id']} — {dtext(dt.date.fromisoformat(s['date']))} — {s['activity']}** ({s['errand']})" + (" *(regenerated)*" if s["regenerated"] else ""))
        V.append("> situation (synthetic_task_context): " + " | ".join(e["text"] for e in s["context"]["elements"].values()))
        V += [f"- `{t['dia_id']}` **{t['speaker']}**: {t['text']}" for t in s["turns"]]
        V.append("")
    if hist["dropped"]:
        V += ["### Dropped sessions\n", "| session | attempt | reasons |", "|---|---|---|"]
        for s in hist["dropped"]:
            why = "; ".join(f"{p.get('type')} [{p.get('source')}]: {p.get('reason')}" for p in s["check"]["problems"]) or s["check"]["status"]
            V.append(f"| {s['session_id']} ({s['activity']}) | {s.get('regenerated', 0)} | {why} |")
    V += ["\n## 4. Extracted memory\n",
          "text label = what the entry states or suggests (annotator). status combines it with how the source was generated: "
          "`verified_cue` (source derives from or was generated together with the attribute), `unsupported_association` "
          "(source was sampled independently of the attribute), `unverified`, `linked_not_apparent`.\n",
          "| id (evidence) | memory | quote | scope / sessions | support | source elements | age | household | employment | income | education |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    cell = lambda a, f: "" if a["text_label"][f] == "none" and a["status"][f] == "none" else f"{a['text_label'][f]} → {a['status'][f]}"
    for it in mem["raw"]:
        a = it["annotation"]
        V.append(f"| {it['memory_id']} ({','.join(it['dialogue_ids'])}) | {it['text']} | “{it['quotes'][0]}” | {it['scope']} / {it['n_sessions']}"
                 f"{' /3rd' if it['subject'] == 'third_party' else ''} | {it['support']} | {', '.join(it['elements']) or 'untraced'} | "
                 + " | ".join(cell(a, f) for f in ATTRS) + " |")
    ac = mem["filtered"]["age_cue_only"]
    V += [f"\n## 5. age_cue_only ({len(ac['memory'])} items)\n"]
    V += (["Removed or split:\n"] + [f"- {r['memory_id']}: “{r['text']}” — {r['reason']}; kept atoms: {r['atoms_kept']}; removed atoms: {r['atoms_removed']}"
                                     for r in ac["removed"]]) if ac["removed"] else ["No direct age statement in the raw memory; this version is identical to it.\n"]
    V += ["\n## 6. Current tasks\n", f"City: {tasks['city']}; catalog: `{tasks['catalog']}`. Budget rule: {tasks['budget_rule']}\n",
          "| activity | request | constraints | participants rule | text label → status |", "|---|---|---|---|---|"]
    for t in tasks["tasks"]:
        a = t["self_leak"]
        leak = ", ".join(f"{f}: {cell(a, f)}" for f in ATTRS if cell(a, f)) or "nothing"
        V.append(f"| {t['activity']} | {t['request']} | {json.dumps(t['constraints'])} | {t['participants_rule']} | {leak}"
                 + (" (group size only)" if a["group_size_cue"] else "") + " |")
    return "\n".join(V) + "\n"


def write_provenance(out):
    up = os.path.join(ROOT, "external", "upstream_templates")
    tdir = os.path.join(out, "templates")
    for sub in ("upstream", "adapted", "diff", "diff_r1_to_r2"):
        os.makedirs(os.path.join(tdir, sub), exist_ok=True)
    shutil.copytree(up, os.path.join(tdir, "upstream"), dirs_exist_ok=True)

    def fn_src(path, name):
        s = open(path).read()
        i = s.index(f"def {name}(")
        j = s.find("\ndef ", i + 1)
        return s[i:j if j > 0 else len(s)]

    def sentences(s):
        return [x.strip() for x in re.split(r"(?<=[.:!?])\s+", " ".join(s.split())) if x.strip()]

    loc = re.search(r'CONVERSATION2FACTS_PROMPT = """(.*?)"""', open(os.path.join(up, "locomo", "memory_utils.py")).read(), re.S).group(1)
    triples = {
        "history__personamem_generate_conversations": (
            fn_src(os.path.join(up, "personamem_v2", "prompts.py"), "generate_conversations").splitlines(),
            inspect.getsource(T1.generate_history_session).splitlines(), inspect.getsource(T.user_simulator_prompt).splitlines()),
        "memory__locomo_CONVERSATION2FACTS_PROMPT": (sentences(loc), sentences(T1.CONVERSATION2FACTS_PROMPT), sentences(T.CONVERSATION2FACTS_PROMPT)),
        "annotation__synthpai_build_tagging_comment_prompt": (
            fn_src(os.path.join(up, "synthpai", "user_bot_system_prompt_builder.py"), "build_tagging_comment_prompt").splitlines(),
            inspect.getsource(T1.build_tagging_memory_prompt).splitlines(), inspect.getsource(T.build_tagging_memory_prompt).splitlines()),
        "added__SESSION_CHECK_PROMPT": ([], T1.SESSION_CHECK_PROMPT.splitlines(), T.SESSION_CHECK_PROMPT.splitlines()),
        "added__CROSS_SESSION_PROMPT": ([], T1.CROSS_SESSION_PROMPT.splitlines(), T.CROSS_SESSION_PROMPT.splitlines()),
    }
    for name, (a, b1, b2) in triples.items():
        if a:
            open(os.path.join(tdir, "upstream", name + ".original.txt"), "w").write("\n".join(a) + "\n")
            open(os.path.join(tdir, "diff", name + ".diff"), "w").write("\n".join(difflib.unified_diff(a, b2, "upstream", "adapted_r2", lineterm="", n=2)) + "\n")
        open(os.path.join(tdir, "adapted", name + ".adapted.txt"), "w").write("\n".join(b2) + "\n")
        open(os.path.join(tdir, "diff_r1_to_r2", name + ".diff"), "w").write("\n".join(difflib.unified_diff(b1, b2, "adapted_r1", "adapted_r2", lineterm="", n=2)) + "\n")
    ex = json.load(open(os.path.join(up, "locomo", "fact_generation_examples_new.json")))
    json.dump(T.fact_examples(ex), open(os.path.join(tdir, "adapted", "memory__fewshot_examples.adapted.json"), "w"), indent=2)
    for name in ("HISTORY_ASSISTANT_PROMPT", "SPLIT_PROMPT", "SUPPORT_PROMPT", "DUPLICATE_PROMPT"):
        open(os.path.join(tdir, "adapted", f"added__{name}.txt"), "w").write(getattr(T, name))
    sites = ["# Where each template is called (revision 2)\n", "| template | called from | line |", "|---|---|---|"]
    for tmpl, fn, mod in (("T.user_simulator_prompt (PersonaMem-v2, user side only)", simulate, "v2r2_dialogue_preview"),
                          ("T.HISTORY_ASSISTANT_PROMPT (added)", simulate, "v2r2_dialogue_preview"),
                          ("T.CONVERSATION2FACTS_PROMPT + fact_examples + render_conversation (LoCoMo)", extract_session, "v2r2_dialogue_preview"),
                          ("T.build_tagging_memory_prompt (SynthPAI D.4)", annotate, "v2r2_dialogue_preview"),
                          ("T.SESSION_CHECK_PROMPT (added)", check_session, "v2r2_dialogue_preview"),
                          ("T.CROSS_SESSION_PROMPT (added)", cross_check, "v2r2_dialogue_preview"),
                          ("T.SUPPORT_PROMPT (added)", support_check, "v2r2_dialogue_preview"),
                          ("T.DUPLICATE_PROMPT (added)", duplicate_groups, "v2r2_dialogue_preview"),
                          ("T.SPLIT_PROMPT (added, unchanged)", build_memory, "v2r2_dialogue_preview")):
        sites.append(f"| {tmpl} | scripts/{mod}.py::{fn.__name__} | {inspect.getsourcelines(fn)[1]} |")
    open(os.path.join(tdir, "CALL_SITES.md"), "w").write("\n".join(sites) + "\n")


# ------------------------------------------------------------------------------------------------------ main

def select_profiles(args):
    """Same selection as revision 1 (same RNG), plus the gender of co-resident adults for relation words."""
    people = [json.loads(l) for l in open(args.input)]
    by_id = {p["profile_id"]: p for p in people}
    households = defaultdict(list)
    for p in people:
        households[p["household_id"]].append(p["profile_id"])
    chosen = [by_id[s["profile_id"]] for s in json.load(open(args.prev_manifest))["personas"]]
    sel_rng = random.Random(f"{args.seed}-select")
    used = {p["household_id"] for p in chosen}
    cands = sorted((p for p in people if 28 <= P1.age_on(p["identity"]["dob"]) <= 45 and p["family"].get("spouse") in by_id
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
        youngest = min(P1.age_on(p["identity"]["dob"]), P1.age_on(sp["identity"]["dob"]))
        n = sel_rng.choice([1, 2])
        ages = sorted((sel_rng.randint(0, min(17, youngest - 20)) for _ in range(n)), reverse=True)
        syn_kids[p["profile_id"]] = [{"child_id": f"syn_child_{p['profile_id'][-4:]}_{i + 1}", "age": a, "sex": sel_rng.choice(["girl", "boy"]),
                                      "parents": [p["profile_id"], sp["profile_id"]], "lives_with_persona": True, "source": "synthetic",
                                      "basis": "rule-added for this preview: 1-2 children, age uniform in [0, min(17, younger parent's age - 20)]"}
                                     for i, a in enumerate(ages)]
    profiles = []
    for i, p in enumerate(chosen + extra):
        pid = f"u{i + 1:03d}"
        pr = P1.build_profile(pid, p, by_id, households, syn_kids.get(p["profile_id"], []), random.Random(f"{args.seed}-profile-{pid}"))
        for a in pr["fields"]["co_resident_adults"]["value"]:
            a["gender"] = by_id[a["profile_id"]]["identity"]["gender"]
        profiles.append(pr)
    return profiles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "data_v2_dialogue_preview_r2"))
    ap.add_argument("--input", default=os.path.join(ROOT, "data_v2_preview", "pf", "us_households.jsonl"))
    ap.add_argument("--prev_manifest", default=os.path.join(ROOT, "data_v2_preview", "manifest.json"))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default="qwen3:32b")
    ap.add_argument("--servers", default="http://localhost:11434=1")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--num_ctx", type=int, default=8192)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--only", default="", help="comma-separated persona ids (for a smoke test)")
    ap.add_argument("--max_sessions", type=int, default=0, help="smoke test: keep only the first N planned sessions")
    args = ap.parse_args()
    P1.POOL = ServerPool(args.servers)
    os.makedirs(args.out, exist_ok=True)
    write_provenance(args.out)
    profiles = select_profiles(args)
    if args.only:
        profiles = [p for p in profiles if p["persona_id"] in args.only.split(",")]
    if args.max_sessions:
        plan0 = P1.plan_sessions
        P1.plan_sessions = lambda rng: plan0(rng)[:args.max_sessions]
    examples = T.fact_examples(json.load(open(os.path.join(ROOT, "external", "upstream_templates", "locomo", "fact_generation_examples_new.json"))))

    def dump(sub, pid, obj):
        os.makedirs(os.path.join(args.out, sub), exist_ok=True)
        json.dump(obj, open(os.path.join(args.out, sub, f"{pid}.json"), "w"), indent=2, ensure_ascii=False)

    def run_persona(pr):
        pid = pr["persona_id"]
        cat = build_catalog(pr, random.Random(f"{args.seed}-catalog-{pid}"))
        standing = build_standing(pr, cat, random.Random(f"{args.seed}-standing-{pid}"))
        hist = build_history(args, pr, cat, standing, random.Random(f"{args.seed}-history-{pid}"))   # no access to tasks
        hist["standing"] = standing
        mem = build_memory(args, pr, hist, examples)
        tasks = build_tasks(args, pr, cat, random.Random(f"{args.seed}-tasks-{pid}"))               # separate RNG stream
        for sub, obj in (("personas", pr), ("catalogs", cat), ("history", hist), ("tasks", tasks),
                         (os.path.join("memory", "raw"), {"persona_id": pid, "memory": mem["raw"], "support_counts": mem["support_counts"],
                                                          "residual_duplicate_groups": mem["residual_duplicate_groups"],
                                                          "source_elements": mem["source_elements"]}),
                         (os.path.join("memory", "filtered", "age_cue_only"), {"persona_id": pid, **mem["filtered"]["age_cue_only"]})):
            dump(sub, pid, obj)
        os.makedirs(os.path.join(args.out, "view"), exist_ok=True)
        open(os.path.join(args.out, "view", f"{pid}.md"), "w").write(view(pr, cat, standing, hist, mem, tasks))
        print(f"{pid}: history {hist['status']} ({len(hist['kept'])} kept, {len(hist['dropped'])} dropped); memory {len(mem['raw'])} items "
              f"(support {mem['support_counts']})", flush=True)
        return pr, hist, mem, tasks

    with cf.ThreadPoolExecutor(len(profiles)) as ex:
        results = list(ex.map(run_persona, profiles))

    json.dump(dict(P1.LOG), open(os.path.join(args.out, "failures_and_repairs.json"), "w"), indent=2, ensure_ascii=False)
    digest = None
    try:
        with urllib.request.urlopen(P1.POOL.servers[0][0] + "/api/tags", timeout=30) as r:
            digest = next((m["digest"] for m in json.loads(r.read())["models"] if m["name"] == args.model), None)
    except Exception:
        pass
    json.dump({"revision": 2, "previous_revision": "data_v2_dialogue_preview (unchanged)", "seed": args.seed, "model": args.model,
               "model_digest": digest, "reference_date": REFERENCE.isoformat(), "history_window": [d.isoformat() for d in WINDOW],
               "input": os.path.relpath(args.input, ROOT), "input_sha256": P1.sha(args.input),
               "code_sha256": {f: P1.sha(os.path.join(HERE, f)) for f in ("v2r2_dialogue_preview.py", "v2r2_templates.py", "v2_dialogue_preview.py", "v2_templates.py")},
               "upstream": json.load(open(os.path.join(ROOT, "external", "upstream_templates", "SOURCES.json"))),
               "profilefoundry": "GitHub generator commit 8239180 (Citation License 1.0); gated HF dataset not used",
               "assistant_public_context": "today's date and weekday, 35-day calendar, home city (account setting); no profile, situation or memory",
               "personas": [{"persona_id": pr["persona_id"], "profile_id": pr["source"]["profile_id"]} for pr, *_ in results],
               "llm_calls": P1.STATS["llm_calls"], "args": {k: v for k, v in vars(args).items() if k != "servers"}},
              open(os.path.join(args.out, "manifest.json"), "w"), indent=2)
    print("done; LLM calls:", P1.STATS["llm_calls"])


if __name__ == "__main__":
    main()
