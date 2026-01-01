"""
Trace Sanitization — remove explicit or direct cues of private attributes from activity traces.
"""

from datasets import load_dataset
from collections import defaultdict
import json

repo = "yonglixiang/AntiSkillBench"

characters = load_dataset(repo, "character")["train"]
questions = load_dataset(repo, "question")["train"]
dialogues = load_dataset(repo, "dialogue")["train"]


# ============================================================
# 1. Index dialogues by question_id
# ============================================================

dialogue_by_question_id = {}

for i, d in enumerate(dialogues):
    qid = d["question"]["question_id"]

    dialogue_by_question_id[qid] = {
        "dialogue_index": i,
        "num_user_turns": sum(
            m["role"] == "user"
            for m in d["dialogue"]
        )
    }


# ============================================================
# 2. Group questions by character
# ============================================================

questions_by_character = defaultdict(list)

for q in questions:
    questions_by_character[q["character_id"]].append(q)


# ============================================================
# 3. Build mapping
# ============================================================

mapping = {}

for c in characters:

    cid = c["character_id"]

    activities = []

    for activity_id, q in enumerate(
        questions_by_character[cid],
        start=1
    ):

        qid = q["question_id"]

        dialogue_info = dialogue_by_question_id.get(qid)

        activity = {
            "activity_id": activity_id,
            "question_id": qid,
            "question_type": q["question_type"],
            "has_dialogue": dialogue_info is not None
        }

        if dialogue_info is not None:
            activity["dialogue_index"] = dialogue_info["dialogue_index"]
            activity["num_user_turns"] = dialogue_info["num_user_turns"]

        activities.append(activity)


    mapping[cid] = {

        "name": c["name"],

        "ground_truth": {
            "age": c["age"],
            "gender": c["gender"],
            "race": c["race"],
            "born_place": c["born place"],
            "occupation": c["occupation"],
            "education": c["education"]
        },

        "activities": activities
    }


# ============================================================
# 4. Save
# ============================================================

with open("mapping.json", "w", encoding="utf-8") as f:
    json.dump(
        mapping,
        f,
        ensure_ascii=False,
        indent=2
    )


print("Saved mapping.json")
print("Characters:", len(mapping))

total_activities = sum(
    len(x["activities"])
    for x in mapping.values()
)

print("Activities:", total_activities)

missing = [
    a
    for person in mapping.values()
    for a in person["activities"]
    if not a["has_dialogue"]
]

print("Activities without dialogue:", len(missing))

