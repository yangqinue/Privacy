from datasets import load_dataset

repo = "yonglixiang/AntiSkillBench"

characters = load_dataset(repo, "character")["train"]
questions = load_dataset(repo, "question")["train"]
dialogues = load_dataset(repo, "dialogue")["train"]


# ============================================================
# Pick one character
# ============================================================

c = characters[0]
cid = c["character_id"]

print("=" * 80)
print("PERSONA")
print("=" * 80)

print("Name:", c["name"])
print("Age:", c["age"])
print("Gender:", c["gender"])
print("Race:", c["race"])
print("Occupation:", c["occupation"])
print("Education:", c["education"])


# ============================================================
# Get this character's questions and dialogues
# ============================================================

qs = questions.filter(
    lambda x: x["character_id"] == cid
)

ds = dialogues.filter(
    lambda x: x["character_id"] == cid
)

print("\nNumber of questions:", len(qs))
print("Number of dialogues:", len(ds))


# ============================================================
# Show first 3 activities
# ============================================================

for i in range(min(3, len(ds))):

    d = ds[i]

    print("\n\n" + "=" * 80)
    print(f"ACTIVITY {i + 1}")
    print("=" * 80)

    # --------------------------------------------------------
    # Original question
    # --------------------------------------------------------

    print("\n[ORIGINAL QUESTION]")

    question_info = d["question"]

    print("Type:", question_info["question_type"])
    print("Question ID:", question_info["question_id"])
    print("Text:")
    print(question_info["question"])


    # --------------------------------------------------------
    # Full dialogue
    # --------------------------------------------------------

    print("\n[FULL DIALOGUE]")

    for turn_id, message in enumerate(d["dialogue"], start=1):

        role = message["role"].upper()

        print(f"\n--- Turn {turn_id}: {role} ---")
        print(message["content"])

