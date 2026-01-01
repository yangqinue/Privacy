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

# print("=" * 80)
# print("PERSONA")
# print("=" * 80)

# print("Name:", c["name"])
# print("Age:", c["age"])
# print("Gender:", c["gender"])
# print("Race:", c["race"])
# print("Occupation:", c["occupation"])
# print("Education:", c["education"])


# ============================================================
# Get this character's questions and dialogues
# ============================================================

qs = questions.filter(
    lambda x: x["character_id"] == cid
)

ds = dialogues.filter(
    lambda x: x["character_id"] == cid
)

# print("\nNumber of questions:", len(qs))
# print("Number of dialogues:", len(ds))


# ============================================================
# Show first 3 activities
# ============================================================

for i in range(min(3, len(ds))):

    d = ds[i]

    # print("\n\n" + "=" * 80)
    # print(f"ACTIVITY {i + 1}")
    # print("=" * 80)

    # --------------------------------------------------------
    # Original question
    # --------------------------------------------------------

    # print("\n[ORIGINAL QUESTION]")

    question_info = d["question"]

    # print("Type:", question_info["question_type"])
    # print("Question ID:", question_info["question_id"])
    # print("Text:")
    # print(question_info["question"])


    # --------------------------------------------------------
    # Full dialogue
    # --------------------------------------------------------

    # print("\n[FULL DIALOGUE]")

    for turn_id, message in enumerate(d["dialogue"], start=1):

        role = message["role"].upper()

        # print(f"\n--- Turn {turn_id}: {role} ---")
        # print(message["content"])





print("\n" + "=" * 80)
print("CHECK DATA ISSUES")
print("=" * 80)


# ============================================================
# 1. Find the question that has no corresponding dialogue
# ============================================================

# All question IDs from question dataset
question_ids = set(questions["question_id"])

# All question IDs that appear in dialogue dataset
dialogue_question_ids = set()

for d in dialogues:
    dialogue_question_ids.add(d["question"]["question_id"])


missing_ids = question_ids - dialogue_question_ids

print("\nQuestions without dialogue:")
print(missing_ids)

for q in questions:
    if q["question_id"] in missing_ids:
        print("\n[MISSING DIALOGUE]")
        print("Character ID:", q["character_id"])
        print("Question ID:", q["question_id"])
        print("Question Type:", q["question_type"])
        print("Question:", q["question"])


# ============================================================
# 2. Find abnormal dialogues
# ============================================================

print("\n" + "=" * 80)
print("ABNORMAL DIALOGUES")
print("=" * 80)

for d in dialogues:

    total_turns = len(d["dialogue"])

    user_turns = sum(
        1 for m in d["dialogue"]
        if m["role"] == "user"
    )

    assistant_turns = sum(
        1 for m in d["dialogue"]
        if m["role"] == "assistant"
    )

    # Normally user and assistant should have same number of turns
    if user_turns != assistant_turns:

        print("\n[INCOMPLETE DIALOGUE]")
        print("Character ID:", d["character_id"])
        print("Question ID:", d["question"]["question_id"])
        print("Question:", d["question"]["question"])

        print("User turns:", user_turns)
        print("Assistant turns:", assistant_turns)
        print("Total turns:", total_turns)

        print("\nDialogue:")

        for i, message in enumerate(d["dialogue"], start=1):
            print(f"\nTurn {i} [{message['role'].upper()}]")
            print(message["content"])