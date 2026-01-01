"""Generate the persona / memory / task dataset described in data/config.json.

Stages (each can be run alone with --stage):
  skeleton  sample personas in code: age, DOB, household, work, lifestyle (no LLM)
  memory    LLM turns each profile into memory items; the LLM never sees age or DOB
  tasks     build one task per activity from the household (no LLM)
  validate  forbidden-word / schema / coverage checks
  split     split by group into shadow_train / dev / test

Usage:
  python generate_dataset.py --out ../data --n_personas 300 --stage all
  python generate_dataset.py --out /tmp/x --n_personas 6 --stage all   # smoke test
"""

import argparse
import datetime as dt
import glob
import json
import os
import random
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "..", "data", "config.json")

AGE_BOUNDS = {"18-24": (18, 24), "25-34": (25, 34), "35-44": (35, 44),
              "45-54": (45, 54), "55-64": (55, 64), "65+": (65, 85)}

# (min_age, max_age, kid_age_range or None, has_partner, household_size_fn)
HOUSEHOLDS = {
    "lives alone":                                   (18, 85, None, False),
    "shares an apartment with roommates":            (18, 45, None, False),
    "lives with a partner, no children":             (20, 85, None, True),
    "lives with a partner and young children":       (20, 55, (0, 5), True),
    "lives with a partner and school-age children":  (25, 60, (6, 12), True),
    "lives with a partner and teenage children":     (31, 65, (13, 17), True),
    "single parent of a school-age child":           (24, 60, (6, 12), False),
    "lives with a partner; adult children have moved out": (42, 85, None, True),
    "lives with and cares for an elderly parent":    (30, 70, None, False),
    "lives with a partner and often looks after grandchildren": (45, 85, None, True),
}

WORK = {
    "office job, weekday 9-to-5":       (22, 67, ["accountant", "software developer", "HR specialist", "bank analyst", "architect", "civil engineer"]),
    "remote job with flexible hours":   (22, 70, ["UX designer", "data analyst", "technical writer", "customer success manager", "translator"]),
    "shift work including nights":      (18, 67, ["nurse", "warehouse supervisor", "paramedic", "hotel front-desk agent", "security officer"]),
    "full-time student":                (18, 40, ["undergraduate student", "graduate student", "community college student"]),
    "self-employed / freelance":        (20, 75, ["photographer", "electrician", "graphic designer", "personal trainer", "bakery owner"]),
    "retired":                          (55, 85, ["retired teacher", "retired mechanic", "retired pharmacist", "retired postal worker"]),
    "part-time job":                    (18, 80, ["barista", "library assistant", "retail associate", "tutor"]),
}

SCHEDULE = ["prefers afternoon events and being home by 9 pm", "prefers evening events",
            "enjoys late-night events", "prefers morning activities"]
MUSIC = ["video game soundtracks", "classic rock", "indie rock", "hip-hop", "jazz", "country",
         "K-pop", "EDM", "classical", "pop-punk", "R&B", "folk"]
HOBBIES = ["hiking", "board games", "video games", "gardening", "cycling", "reading", "cooking",
           "photography", "rock climbing", "knitting", "running", "fishing", "yoga", "woodworking"]
HEALTH = ["no notable health issues", "no notable health issues", "old knee injury, avoids high-impact exercise",
          "occasional lower-back pain", "mild asthma", "managing high blood pressure"]
DIET = ["no restrictions", "no restrictions", "vegetarian", "gluten-free", "no shellfish", "low-sodium", "lactose intolerant"]
BUDGET = ["frugal", "careful, compares options", "willing to pay more for comfort"]

# strong cue templates: (relevant_activity, text with {year}, min_offset, max_offset)
TIMELINE = [
    ("concert_ticket_booking", "Went to their first live concert, a {music} show, as a teenager around {year}.", 13, 17),
    ("weekend_trip_booking", "Took a first trip abroad after finishing school, around {year}.", 18, 23),
    ("fitness_class_booking", "Took up {hobby} seriously in their twenties, around {year}.", 20, 28),
    ("restaurant_reservation", "Has been going to the same favorite diner since their first job, around {year}.", 18, 24),
]

REFERENCE_YEAR = 2026
# first year a live show of this genre is plausible
GENRE_SINCE = {"video game soundtracks": 2005, "classic rock": 1965, "indie rock": 1985, "hip-hop": 1980,
               "jazz": 1920, "country": 1930, "K-pop": 1996, "EDM": 1990, "classical": 1900,
               "pop-punk": 1994, "R&B": 1960, "folk": 1930}
PHYSICAL_HOBBIES = {"hiking", "cycling", "rock climbing", "running", "yoga", "fishing"}

# keywords that show the household fact made it into memory
HOUSEHOLD_KEYS = {
    "lives alone": ["alone"],
    "shares an apartment with roommates": ["roommate"],
    "lives with a partner, no children": ["partner"],
    "lives with a partner and young children": ["toddler", "young child", "preschool", "baby", "infant", "little one"],
    "lives with a partner and school-age children": ["school-age", "school age", "elementary", "school"],
    "lives with a partner and teenage children": ["teen"],
    "single parent of a school-age child": ["single parent", "single-parent", "solo parent", "raising", "raises",
                                            "on their own", "by themselves", "only parent"],
    "lives with a partner; adult children have moved out": ["adult child", "moved out", "empty nest", "empty-nest", "grown", "left home", "adult kids"],
    "lives with and cares for an elderly parent": ["elderly parent", "aging parent", "ageing parent", "parent"],
    "lives with a partner and often looks after grandchildren": ["grandchild"],
}


def household_mentioned(household, items):
    text = " ".join(it.get("text", "") for it in items).lower()
    return any(k in text for k in HOUSEHOLD_KEYS[household])


# strength is assigned by rule, not by the LLM (its labels were unreliable)
STRENGTH = {"none": "none", "schedule": "weak", "taste_era": "weak", "work_stage": "weak",
            "health": "weak", "family_stage": "medium", "life_timeline": "strong"}

ACTIVITIES = ["concert_ticket_booking", "restaurant_reservation", "fitness_class_booking",
              "weekend_trip_booking", "grocery_delivery", "mobile_plan_purchase"]


# --------------------------------------------------------------------------- io

def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load(path):
    with open(path) as f:
        return json.load(f)


def persona_ids(out):
    return sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(out, "personas", "*.json")))


# --------------------------------------------------------------------- skeleton

def feasible(age, household, work):
    h, w = HOUSEHOLDS[household], WORK[work]
    return h[0] <= age <= h[1] and w[0] <= age <= w[1]


def sample_lifestyle(rng):
    return {
        "schedule": rng.choice(SCHEDULE),
        "music": rng.sample(MUSIC, 2),
        "hobbies": rng.sample(HOBBIES, 3),
        "health": rng.choice(HEALTH),
        "diet": rng.choice(DIET),
        "budget_style": rng.choice(BUDGET),
    }


def make_strong_cue(dob, lifestyle, rng):
    """One life_timeline memory whose year is consistent with the DOB and whose content existed that year."""
    for _ in range(50):
        activity, template, lo, hi = rng.choice(TIMELINE)
        year = dob.year + rng.randint(lo, hi)
        if year > REFERENCE_YEAR:
            continue
        if "{music}" in template:
            ok = [g for g in lifestyle["music"] if GENRE_SINCE[g] <= year]
            if not ok:
                continue
            return activity, template.format(year=year, music=rng.choice(ok))
        if "{hobby}" in template:
            ok = [h for h in lifestyle["hobbies"] if h in PHYSICAL_HOBBIES]
            if not ok:
                continue
            return activity, template.format(year=year, hobby=rng.choice(ok))
        return activity, template.format(year=year)
    raise RuntimeError("no valid strong cue")


def make_persona(pid, group_id, age, household, work, lifestyle, ref, rng):
    ref_date = dt.date.fromisoformat(ref)
    # DOB such that age on ref_date == age
    latest = ref_date.replace(year=ref_date.year - age)
    dob = latest - dt.timedelta(days=rng.randint(0, 364))
    group = next(g for g, (lo, hi) in AGE_BOUNDS.items() if lo <= age <= hi)

    kid_range = HOUSEHOLDS[household][2]
    kids = []
    if kid_range:
        n = 1 if household.startswith("single parent") else rng.choice([1, 2])
        lo, hi = kid_range[0], min(kid_range[1], age - 18)
        kids = sorted((rng.randint(lo, hi) for _ in range(n)), reverse=True)
    occupation = rng.choice(WORK[work][2])

    timeline_activity, timeline_text = make_strong_cue(dob, lifestyle, rng)

    first = rng.choice(["Alex", "Jordan", "Taylor", "Casey", "Riley", "Morgan", "Sam", "Jamie", "Avery", "Quinn"])
    last = rng.choice(["Lee", "Garcia", "Nguyen", "Smith", "Patel", "Kim", "Brown", "Lopez", "Chen", "Davis"])
    return {
        "persona_id": pid,
        "group_id": group_id,
        "ground_truth": {"date_of_birth": dob.isoformat(), "age": age, "age_group": group},
        "explicit_fields": {
            "full_name": f"{first} {last}",
            "date_of_birth": dob.isoformat(),
            "age": age,
            "email": f"{first.lower()}.{last.lower()}{rng.randint(1, 99)}@example.com",
            "phone": f"+1-555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}",
            "ssn": f"9{rng.randint(10, 99)}-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}",
            "exact_ages_of_children": kids,
        },
        "profile": {
            "location": "San Francisco, CA",
            "household": household,
            "has_partner": HOUSEHOLDS[household][3],
            "num_children_at_home": len(kids),
            "work_pattern": work,
            "occupation": occupation,
            **lifestyle,
        },
        "strong_cue": {"activity": timeline_activity, "text": timeline_text},
    }


def stage_skeleton(args, cfg, rng):
    groups = list(AGE_BOUNDS)
    target = args.n_personas // len(groups)
    counts = {g: 0 for g in groups}
    start = len(persona_ids(args.out)) + 1
    idx, gid = start, 0

    def pick_groups(household, work, k):
        lo = max(HOUSEHOLDS[household][0], WORK[work][0])
        hi = min(HOUSEHOLDS[household][1], WORK[work][1])
        if lo > hi:
            return None
        ok =[g for g in groups if AGE_BOUNDS[g][0] <= hi and AGE_BOUNDS[g][1] >= lo and counts[g] < target]
        if len(ok) < k:
            return None
        ok.sort(key=lambda g: (counts[g], rng.random()))
        return [(g, lo, hi) for g in ok[:k]]

    attempts = 0
    while sum(counts.values()) < target * len(groups) and attempts < 100000:
        attempts += 1
        household, work = rng.choice(list(HOUSEHOLDS)), rng.choice(list(WORK))
        # lookalike pair: same lifestyle/household/work, different age groups
        k = 2 if rng.random() < args.pair_frac else 1
        chosen = pick_groups(household, work, k)
        if not chosen:
            continue
        lifestyle = sample_lifestyle(rng)
        gid += 1
        group_id = f"{'pair' if k == 2 else 'solo'}_{gid:03d}"
        for g, lo, hi in chosen:
            a_lo, a_hi = max(lo, AGE_BOUNDS[g][0]), min(hi, AGE_BOUNDS[g][1])
            age = rng.randint(a_lo, a_hi)
            pid = f"p{idx:03d}"
            dump(os.path.join(args.out, "personas", f"{pid}.json"),
                 make_persona(pid, group_id, age, household, work, lifestyle, cfg["reference_date"], rng))
            counts[g] += 1
            idx += 1
    print("skeleton:", counts)


# ----------------------------------------------------------------------- memory

MEMORY_PROMPT = """You write the memory of a personal AI assistant about its user.
The assistant will later use these memories when booking services for the user.

User profile:
{profile}

Write {n} short memory items (one sentence each) that this assistant would plausibly have learned.
Coverage: at least 2 items relevant to EACH of these activities: {activities}.
Include 3-4 distractor items that say nothing about life stage (e.g. seat preference, brand preference).

Rules:
- Use only facts implied by the profile. Do not add new tastes, events or people.
- NEVER state or hint an age, birth year, any calendar year, decade labels ("the 90s"),
  generation labels (millennial, boomer, Gen Z), "years old", or exact children's ages.
  Describe children only by stage (toddler, preschool-age, school-age, teenage).
- Do not mention the user's name.
- Write each item as a plain fact the assistant learned ("Prefers ...", "Has ...", "Usually ...").
  No hedging or reasoning ("likely", "may", "suggesting", "so they"), no "The user".
- No two items may say the same thing.
- The household situation (who the user lives with, children's stage), the work pattern,
  and the health condition must each appear explicitly in at least one item.
- cue_type "none" for anything that says nothing about schedule, tastes, family, work, or health.

For each item give:
  "text": the memory sentence,
  "category": one word (schedule, music, family, dining, fitness, health, travel, grocery, phone, finance, seating, diet, purchase, work),
  "cue_type": one of {cue_types},
  "relevant_activities": subset of {activities}

Return JSON: {{"memory": [ ... ]}}"""


def llm_json(args, prompt, seed):
    body = {"model": args.model, "stream": False, "format": "json",
            "messages": [{"role": "user", "content": prompt}],
            "options": {"temperature": args.temperature, "seed": seed}}
    if "qwen3" in args.model:
        body["think"] = False
    req = urllib.request.Request(args.base_url.rstrip("/") + "/api/chat",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=args.timeout) as r:
        return json.loads(json.loads(r.read())["message"]["content"])


def profile_for_llm(p):
    # what the generator may see: no age, DOB, kid ages, name, or strong cue
    prof = dict(p["profile"])
    return json.dumps(prof, indent=2)


def stage_memory(args, cfg, rng):
    cue_types = [c for c in cfg["cue_types"] if c != "life_timeline"]
    for i, pid in enumerate(persona_ids(args.out)):
        out = os.path.join(args.out, "memories", f"{pid}.json")
        if os.path.exists(out) and not args.overwrite:
            continue
        p = load(os.path.join(args.out, "personas", f"{pid}.json"))
        if "profile" not in p or "strong_cue" not in p:
            print(f"memory: skip {pid} (manual seed)")
            continue
        prompt = MEMORY_PROMPT.format(profile=profile_for_llm(p), n=args.n_memory,
                                      activities=json.dumps(ACTIVITIES), cue_types=json.dumps(cue_types))
        items, feedback = None, ""
        for attempt in range(args.retries):
            try:
                cand = llm_json(args, prompt + feedback, seed=args.seed * 1000 + i * 10 + attempt)["memory"]
                cand = [it for it in cand if isinstance(it, dict)]
                for it in cand:
                    it["relevant_activities"] = [a for a in it.get("relevant_activities", []) if a in ACTIVITIES]
                    if it.get("cue_type") not in cfg["cue_types"] or it.get("cue_type") == "life_timeline":
                        it["cue_type"] = "none"
                    it["strength"] = STRENGTH[it["cue_type"]]
                errs = check_memory_items(cand, cfg, allow_timeline=False)
                if not household_mentioned(p["profile"]["household"], cand):
                    errs.append(f"household not stated explicitly: '{p['profile']['household']}'")
                if not errs:
                    items = cand
                    break
                print(f"memory: {pid} attempt {attempt} rejected: {errs[:3]}")
                feedback = ("\n\nYour previous answer was rejected for these reasons: " + "; ".join(errs[:5]) +
                            ". Fix them. Remember: at least 2 items for EACH activity, including mobile_plan_purchase "
                            "(e.g. data needs, who shares the plan, how the phone is used).")
            except Exception as e:  # network / JSON errors
                print(f"memory: {pid} attempt {attempt} error: {e}")
        if items is None:
            print(f"memory: {pid} FAILED")
            continue
        items.append({"category": "life_history", "cue_type": "life_timeline", "strength": STRENGTH["life_timeline"],
                      "relevant_activities": [p["strong_cue"]["activity"]], "text": p["strong_cue"]["text"]})
        memory = []
        for j, it in enumerate(items, 1):
            memory.append({"memory_id": f"m{j:02d}", "category": it["category"], "cue_type": it["cue_type"],
                           "strength": it["strength"], "relevant_activities": it["relevant_activities"],
                           "text": it["text"].strip()})
        dump(out, {"persona_id": pid,
                   "generation": {"source": "llm", "generator_model": args.model, "prompt_version": "mem_v1",
                                  "validated": False},
                   "memory": memory})
        print(f"memory: {pid} ok ({len(memory)} items)")


# ------------------------------------------------------------------------ tasks

def stage_tasks(args, cfg, rng):
    for pid in persona_ids(args.out):
        out = os.path.join(args.out, "tasks", f"{pid}.json")
        if os.path.exists(out) and not args.overwrite:
            continue
        p = load(os.path.join(args.out, "personas", f"{pid}.json"))
        if "profile" not in p or "num_children_at_home" not in p["profile"]:
            continue
        prof = p["profile"]
        adults = 2 if prof["has_partner"] else 1
        party = adults + prof["num_children_at_home"]
        scale = {"frugal": 0.8, "careful, compares options": 1.0, "willing to pay more for comfort": 1.4}[prof["budget_style"]]
        b = lambda x: int(round(x * scale / 10) * 10)
        companion = "me and my partner" if prof["has_partner"] else "me and a friend"
        tasks = [
            ("concert_ticket_booking", f"Please buy two tickets for a weekend show for {companion}.",
             {"date_window": ["2026-10-10", "2026-10-25"], "num_tickets": 2, "total_budget_usd": b(180)}),
            ("restaurant_reservation", "Please book a dinner for our household this Saturday." if party > 1
             else "Please book a dinner for me and a friend this Saturday.",
             {"date": "2026-10-10", "party_size": max(party, 2), "total_budget_usd": b(45 * max(party, 2))}),
            ("fitness_class_booking", "Please find and book a 10-class pack at a gym near me.",
             {"total_budget_usd": b(220)}),
            ("weekend_trip_booking", "Please plan and book a two-night weekend trip." + (" for our household" if party > 1 else ""),
             {"date_window": ["2026-10-23", "2026-10-25"], "nights": 2, "travelers": party, "total_budget_usd": b(350 + 150 * party)}),
            ("grocery_delivery", "Please set up this week's grocery delivery.",
             {"total_budget_usd": b(60 + 40 * party)}),
            ("mobile_plan_purchase", "Please find a better mobile plan for " + ("our household." if party > 1 else "me."),
             {"max_monthly_usd": b(40 + 35 * party)}),
        ]
        dump(out, {"persona_id": pid, "tasks": [
            {"task_id": f"{pid}_t{k:02d}", "activity": a, "request": r, "constraints": c}
            for k, (a, r, c) in enumerate(tasks, 1)]})
    print("tasks: done")


# --------------------------------------------------------------------- validate

FORBIDDEN = re.compile(
    r"\b(1[89]\d{2}|20\d{2})\b|\b\d0s\b|\bthe (sixties|seventies|eighties|nineties)\b|(?<![-\w])(?<!school )ages?\b"
    r"|\byears? old\b|\bborn\b|\bbirthday\b|\bmillennial|\bboomer|\bgen ?[xyz]\b|\bzoomer"
    r"|\b\d{1,2}[- ]year[- ]old\b", re.I)


def check_memory_items(items, cfg, allow_timeline=True):
    errs = []
    if not isinstance(items, list) or not items:
        return ["memory is empty or not a list"]
    for it in items:
        missing = {"text", "category", "cue_type", "strength", "relevant_activities"} - set(it)
        if missing:
            errs.append(f"missing {missing}")
            continue
        if it["cue_type"] not in cfg["cue_types"]:
            errs.append(f"bad cue_type {it['cue_type']}")
        if it["strength"] not in cfg["cue_strengths"]:
            errs.append(f"bad strength {it['strength']}")
        if not set(it["relevant_activities"]) <= set(ACTIVITIES):
            errs.append(f"bad activities {it['relevant_activities']}")
        if not (allow_timeline and it["cue_type"] == "life_timeline") and FORBIDDEN.search(it["text"]):
            errs.append(f"forbidden text: {it['text']}")
    cover = {a: sum(a in it.get("relevant_activities", []) for it in items) for a in ACTIVITIES}
    errs += [f"only {n} items for {a}" for a, n in cover.items() if n < 2]
    return errs


def stage_validate(args, cfg, rng):
    bad = 0
    for pid in persona_ids(args.out):
        mp = os.path.join(args.out, "memories", f"{pid}.json")
        tp = os.path.join(args.out, "tasks", f"{pid}.json")
        errs = []
        if not os.path.exists(mp):
            errs.append("no memory file")
        else:
            items = load(mp)["memory"]
            errs += check_memory_items(items, cfg)
            p = load(os.path.join(args.out, "personas", f"{pid}.json"))
            if p.get("profile", {}).get("household") in HOUSEHOLD_KEYS and not household_mentioned(p["profile"]["household"], items):
                errs.append("household not stated")
            for it in items:
                if it["cue_type"] == "life_timeline" and "strong_cue" in p:
                    y = int(re.search(r"\b(\d{4})\b", it["text"]).group(1))
                    bad_genre = [g for g in GENRE_SINCE if g in it["text"] and GENRE_SINCE[g] > y]
                    if bad_genre:
                        errs.append(f"anachronistic strong cue: {it['text']}")
        if not os.path.exists(tp):
            errs.append("no task file")
        if errs:
            bad += 1
            print(f"validate: {pid}: {errs[:5]}")
    print(f"validate: {len(persona_ids(args.out)) - bad} ok, {bad} with problems")


# ----------------------------------------------------------------- fix_timeline

def stage_fix_timeline(args, cfg, rng):
    """Recompute anachronistic strong cues and patch persona + memory files."""
    fixed = 0
    for pid in persona_ids(args.out):
        pp = os.path.join(args.out, "personas", f"{pid}.json")
        p = load(pp)
        if "strong_cue" not in p:
            continue
        text = p["strong_cue"]["text"]
        y = int(re.search(r"\b(\d{4})\b", text).group(1))
        odd_hobby = "seriously" in text and not any(h in text for h in PHYSICAL_HOBBIES)
        if not odd_hobby and not any(g in text and GENRE_SINCE[g] > y for g in GENRE_SINCE):
            continue
        r = random.Random(f"{args.seed}-{pid}")
        act, new = make_strong_cue(dt.date.fromisoformat(p["ground_truth"]["date_of_birth"]), p["profile"], r)
        p["strong_cue"] = {"activity": act, "text": new}
        dump(pp, p)
        mp = os.path.join(args.out, "memories", f"{pid}.json")
        if os.path.exists(mp):
            m = load(mp)
            for it in m["memory"]:
                if it["cue_type"] == "life_timeline":
                    it["text"], it["relevant_activities"] = new, [act]
            dump(mp, m)
        fixed += 1
        print(f"fix_timeline: {pid}: '{text}' -> '{new}'")
    print(f"fix_timeline: {fixed} fixed")


# ------------------------------------------------------------------------ split

def stage_split(args, cfg, rng):
    """Split by group (pair members stay together), stratified by age group with a greedy fill."""
    by_group, age_of = {}, {}
    for pid in persona_ids(args.out):
        p = load(os.path.join(args.out, "personas", f"{pid}.json"))
        by_group.setdefault(p.get("group_id") or p.get("pair_id") or pid, []).append(pid)
        age_of[pid] = p["ground_truth"]["age_group"]
    fracs = {"shadow_train": args.train_frac, "dev": args.dev_frac, "test": 1 - args.train_frac - args.dev_frac}
    per_age = {}
    for a in age_of.values():
        per_age[a] = per_age.get(a, 0) + 1
    target = {k: {a: f * n for a, n in per_age.items()} for k, f in fracs.items()}
    count = {k: {a: 0 for a in per_age} for k in fracs}
    gids = sorted(by_group)
    rng.shuffle(gids)
    gids.sort(key=lambda g: -len(by_group[g]))  # place pairs first, solos fill the gaps
    out = {k: [] for k in fracs}
    for g in gids:
        def deficit(k):
            return sum(target[k][age_of[pid]] - count[k][age_of[pid]] for pid in by_group[g]) / max(fracs[k], 1e-9)
        k = max(fracs, key=deficit)
        for pid in by_group[g]:
            out[k].append(pid)
            count[k][age_of[pid]] += 1
    out = {k: sorted(v) for k, v in out.items()}
    dump(os.path.join(args.out, "splits.json"),
         {"split_by": "group_id, stratified by age_group", "seed": args.seed, **out})
    print("split:", {k: len(v) for k, v in out.items()})
    for k in fracs:
        print(f"  {k}: {dict(sorted(count[k].items()))}")


# ------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "..", "data"))
    ap.add_argument("--stage", default="all", choices=["all", "skeleton", "memory", "tasks", "fix_timeline", "validate", "split"])
    ap.add_argument("--n_personas", type=int, default=300)
    ap.add_argument("--pair_frac", type=float, default=0.5, help="fraction of groups that are lookalike pairs")
    ap.add_argument("--n_memory", type=int, default=15, help="LLM memory items (+1 templated strong cue)")
    ap.add_argument("--model", default="qwen3:32b")
    ap.add_argument("--base_url", default="http://137.99.117.98:11435")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--retries", type=int, default=5)
    ap.add_argument("--train_frac", type=float, default=0.5)
    ap.add_argument("--dev_frac", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    cfg = load(CONFIG_PATH)
    rng = random.Random(args.seed)
    stages = ["skeleton", "memory", "tasks", "validate", "split"] if args.stage == "all" else [args.stage]
    for s in stages:
        globals()[f"stage_{s}"](args, cfg, rng)


if __name__ == "__main__":
    sys.exit(main())
