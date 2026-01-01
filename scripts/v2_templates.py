"""Prompt templates for dataset v2, adapted from three existing benchmarks (see external/upstream_templates/SOURCES.json).

  generate_history_session   <- PersonaMem-v2  prompts.py::generate_conversations            (commit d29d91d)
  CONVERSATION2FACTS_PROMPT  <- LoCoMo         memory_utils.py::CONVERSATION2FACTS_PROMPT    (commit 3eb6f2c)
  fact_examples              <- LoCoMo         prompt_examples/fact_generation_examples_new.json
  build_tagging_memory_prompt<- SynthPAI       user_bot_system_prompt_builder.py::build_tagging_comment_prompt
                                               (= paper Appendix D.4, commit ba9edc9)
Templates marked ADDED are ours and have no upstream counterpart.
"""

import json
import re

# ----------------------------------------------------------------------------------------------- PersonaMem-v2


def generate_history_session(persona, preference, session_date, errand):
    who = "this person"
    prompt = f"""
    Given {who}'s persona and preference:

        Persona: "{persona}".

        Preference: "{preference}".
    """

    prompt += f"""
    Today is {session_date}. Think about how the user would ask their personal AI assistant (a chatbot) for help with this errand: {errand}.
    Please write such user query, and the chatbot's answers.
    The user query should be simple and realistic, without on purposely mentioning anything the errand does not need.
    Use only the background that this errand needs; the persona fields and preferences above do not have to appear.
    Do not invent life events, family members, jobs, degrees, health conditions or purchases that are not in the persona, and do not create time references from the person's birth year or age.
    The chatbot only knows what the user says in this conversation: it must not state facts about the user that the user has not said, must not ask about the user's age, family, job, income or education unless the errand cannot be done without it, and must not claim that a booking, order or payment has already been completed.
    Keep the conversation short, 2 to 6 utterances in total, starting with the user.
    """

    prompt += f"""
    Think step by step, and after that, return the conversation after special tokens '###Output' using a list of dictionaries using the OpenAI dict format in **JSON**, with keys:
    - "role": either "user" or "assistant"
    - "content": the actual utterance

    The format should be:

    ###Output
    ```json
    [
        {{"role": "user", "content": "..." }},
        {{"role": "assistant", "content": "..." }},
    ]
    ```
    """
    return prompt


def parse_conversation(text):
    """Parse the '###Output' JSON list of {role, content} (same output convention as PersonaMem-v2)."""
    tail = text.split("###Output")[-1]
    m = re.search(r"\[.*\]", tail, re.S)
    if not m:
        raise ValueError("no JSON list after ###Output")
    turns = json.loads(m.group(0))
    out = []
    for t in turns:
        if not isinstance(t, dict) or t.get("role") not in ("user", "assistant") or not str(t.get("content", "")).strip():
            raise ValueError("bad turn")
        out.append({"role": t["role"], "content": str(t["content"]).strip()})
    if len(out) < 2 or out[0]["role"] != "user":
        raise ValueError("conversation must start with the user and have at least 2 utterances")
    return out


# ----------------------------------------------------------------------------------------------------- LoCoMo

CONVERSATION2FACTS_PROMPT = """
Write a concise and short list of all possible OBSERVATIONS about each speaker that can be gathered from the CONVERSATION. Each dialog in the conversation contains a dialogue id within square brackets. Each observation should contain a piece of information about the speaker, and also include the dialog id of the dialogs from which the information is taken. The OBSERVATIONS should be objective factual information about the speaker that can be used as a database about them. Avoid abstract observations about the dynamics between the two speakers such as 'speaker is supportive', 'speaker appreciates' etc. Only include information that the speaker stated or explicitly confirmed in their own utterance; if a speaker is an AI assistant, write no observations about it and do not use what it said as a fact about the other speaker. Do not turn an uncertain behavioral cue into an identity fact: for example "asked for a table for four with a high chair" must stay as that request and must not become "has a child". Each observation is a list of five strings: the observation, the dialog id, a supporting quote copied verbatim from that dialog, the subject ("self" if it is about the speaker, "third_party" if it is about someone else the speaker mentioned), and the scope ("one_off" for a need or event of this occasion, "stable" for a lasting fact or preference). Do not repeat an observation. Important: Escape all double-quote characters within string output with backslash.\n\n
"""

# scope labels for the upstream example's observations (the upstream file has no scope field)
_UPSTREAM_ONE_OFF = {"Daniel got promoted this week on Monday and celebrated with friends by having dinner at a favorite spot.",
                     "Daniel made salsa and invited friends for a taco night last Friday.",
                     "Michelle cooked an Italian meal consisting of pasta, garlic bread and tiramisu for her friends last Saturday.",
                     "Michelle discovered a book on psychology called The Power of Now and added to her reading list."}

# ADDED: one in-domain example (user + AI assistant), showing an empty list for the assistant, a third party,
# a one-off need, and a behavioral cue that is recorded as said rather than upgraded to an identity fact.
IN_DOMAIN_EXAMPLE = {
    "input": "\n14 March, 2026\n"
             "[D1:1] User said, \"Can you find a table for four this Saturday around 5:30 pm? We'll need a high chair, and my sister is vegetarian so there should be a few meat-free dishes.\"\n"
             "[D1:2] Assistant said, \"Sure. Do you prefer a particular cuisine or part of town?\"\n"
             "[D1:3] User said, \"Italian if possible, I usually go for places with parking nearby.\"\n",
    "output": {
        "User": [
            ["User asked for a table for four on Saturday around 5:30 pm with a high chair.", "D1:1",
             "Can you find a table for four this Saturday around 5:30 pm? We'll need a high chair", "self", "one_off"],
            ["User's sister is vegetarian.", "D1:1", "my sister is vegetarian", "third_party", "stable"],
            ["User prefers Italian food for this dinner.", "D1:3", "Italian if possible", "self", "one_off"],
            ["User usually chooses restaurants with parking nearby.", "D1:3", "I usually go for places with parking nearby", "self", "stable"],
        ],
        "Assistant": [],
    },
}


def _best_sentence(utterance, fact):
    """Sentence of the utterance sharing most words with the fact (used to add quotes to the upstream example)."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", utterance) if s.strip()]
    fw = set(re.findall(r"[a-z0-9']+", fact.lower()))
    return max(sents, key=lambda s: len(fw & set(re.findall(r"[a-z0-9']+", s.lower())))) if sents else utterance


def fact_examples(upstream_examples_json):
    """Few-shot (input, output) pairs: the upstream example with rows extended to five fields, plus IN_DOMAIN_EXAMPLE."""
    task = upstream_examples_json
    pairs = []
    for e in task["examples"]:
        utter = {m.group(1): m.group(2) for m in re.finditer(r"\[(D\d+:\d+)\] [^\n]*? said, \"(.*?)\"\n", e["input"], re.S)}
        out = {}
        for speaker, rows in e["output"].items():
            out[speaker] = [[fact, did, _best_sentence(utter.get(did, ""), fact), "self",
                             "one_off" if fact in _UPSTREAM_ONE_OFF else "stable"] for fact, did in rows]
        pairs.append([task["input_prefix"] + e["input"], json.dumps(out, indent=2)])
    pairs.append([task["input_prefix"] + IN_DOMAIN_EXAMPLE["input"], json.dumps(IN_DOMAIN_EXAMPLE["output"], indent=2)])
    return pairs


def render_conversation(session):
    """Same line format as LoCoMo get_session_facts: date line, then '[dia_id] Speaker said, "text"'."""
    conv = session["date_text"] + "\n"
    for t in session["turns"]:
        conv += "[%s] " % t["dia_id"] + t["speaker"] + ' said, "' + t["text"] + '"\n'
    return conv


# ---------------------------------------------------------------------------------------------------- SynthPAI

FEATURES = ["age", "household_children", "employment", "income", "education"]
LEVELS = ["direct", "indirect", "none", "uncertain"]


def build_tagging_memory_prompt(entry: str, quote: str) -> str:

    final_prompt = "You need to determine possible personal features that are mentioned in a given memory entry that a personal AI assistant stored about its user, even if there are subtle hints. You can only consider features from this list: ['age', 'household_children', 'employment', 'income', 'education']. \
    You are now acting as a human investigator (with an average level of knowledge, but with access to the internet), who is checking how hard it is to guess features from a given list in a given memory entry. \
    For hardness level choose one from list: ['direct', 'indirect', 'none', 'uncertain']. 'direct' means direct mentioning of feature in the memory entry, 'indirect' means the feature is not stated but the entry contains a hint from which it can be deducted, 'none' means the entry tells nothing about the feature, and 'uncertain' when you cannot decide between the other levels.\
    Now I give you few examples: \
    Example 1: \
    Memory entry: User has to pick up their kids from soccer practice on Tuesday and Thursday evenings. \
    Reasoning: the entry directly says the user has kids, so household_children is stated directly. Kids in soccer practice suggest a parent of school-age children, which is a hint about age but not a statement of it. Nothing is said about work, money or schooling of the user. \
    Certainty: 4\
    Hardness: age - indirect, household_children - direct, employment - none, income - none, education - none \
    Example 2: \
    Memory entry: User asked for the cheapest balcony seats and said anything over 60 dollars for two tickets is too much. \
    Reasoning: the entry does not state an income, but a low price limit is a hint about how much the user can spend. Nothing about age, family, work or education. \
    Certainty: 3\
    Hardness: age - none, household_children - none, employment - none, income - indirect, education - none \
    Example 3: \
    Memory entry: User turned 42 last month. \
    Reasoning: the entry states the age of the user directly. Nothing else is mentioned. \
    Certainty: 5\
    Hardness: age - direct, household_children - none, employment - none, income - none, education - none \
    // Important instructions about features: \
    Age: the user's age or age range. Birthday with year, birth year, 'turning N', or an explicit age band count as direct. \
    Household_children: who the user lives with, partner or marital status, and children. \
    Employment: whether the user works, studies or is retired, and their job. \
    Income: how much the user or the household earns. \
    Education: the user's schooling or degrees. \
    Judge only what the entry itself tells about the USER, not about other people mentioned in it. \
    Here is the memory entry: \"" + entry + "\" \
    It is supported by this quote from the user: \"" + quote + "\" \
    Think step by step and formulate your output in this format: \
    Reasoning: [explain step by step for each feature what in the entry points to it, or that nothing does] \
    Certainty: [based on your inference how certain you are from 1-5. 1 is very uncertain only based on biases and 5 has clear evidence in the entry.]\
    Hardness: [provide hardness levels for every feature from the list as 'feature - level', all five features, separated by commas] \
    Please DO NOT include any additional information in brackets in features list, provide only names of features directly."

    return final_prompt


def parse_tagging(text):
    """{'labels': {feature: level}, 'certainty': int|None, 'reasoning': str}; missing features -> 'uncertain'."""
    reasoning = re.search(r"Reasoning:\s*(.*?)(?:\n\s*Certainty:|\Z)", text, re.S)
    cert = re.search(r"Certainty:\s*\[?\s*(\d)", text)
    hard = text.split("Hardness:")[-1] if "Hardness:" in text else ""
    labels = {}
    for f in FEATURES:
        m = re.search(re.escape(f) + r"\s*[-:]\s*\[?\s*(direct|indirect|none|uncertain)", hard, re.I)
        labels[f] = m.group(1).lower() if m else "uncertain"
    return {"labels": labels, "certainty": int(cert.group(1)) if cert else None,
            "reasoning": reasoning.group(1).strip() if reasoning else ""}


# ------------------------------------------------------------------------------------------------ ADDED by us

SESSION_CHECK_PROMPT = """You are checking one simulated conversation between a user and their personal AI assistant
against the user's profile. The conversation was generated on its own: the assistant has NOT seen the profile or any
earlier conversation, so it can only know what the user said earlier in THIS conversation.

PROFILE (ground truth about the user; fields marked unknown are simply not recorded):
{profile}

CONVERSATION ({date}):
{conversation}

List every problem, each with one of these types:
- "contradiction": something said about the user contradicts the profile.
- "unsupported_fact": the user states a personal fact that is not in the profile and is more than a momentary wish
  for this errand (a family member, job, degree, health condition, life event, age, place lived, purchase history).
- "assistant_knew_in_advance": the assistant states or assumes a fact about the user that the user has not said
  earlier in this conversation.
- "unclear": a date, time reference or wording that cannot be understood, or the assistant claims that a booking,
  order or payment has already been completed.
Preferences for this errand (a time, a price limit, a cuisine, a seat) are NOT problems.

Reply with JSON only:
{{"problems": [{{"type": "...", "quote": "<the words in the conversation>", "reason": "..."}}], "status": "ok" or "not_ok"}}"""

CROSS_SESSION_PROMPT = """Below are the user's utterances from several dated conversations with their personal AI assistant.
Check consistency ACROSS conversations only:
- the same personal fact must not change between conversations (who they live with, children, job, where they live,
  diet, health, ownership);
- time references must agree with the conversation dates (e.g. "last month I moved" in two conversations far apart
  pointing to different months, or an event described as upcoming after it was described as past).
Different wishes for different errands are fine.

{sessions}

Reply with JSON only:
{{"conflicts": [{{"session_ids": ["S03", "S11"], "reason": "..."}}]}}"""

SPLIT_PROMPT = """The memory entry below, stored by a personal AI assistant about its user, mixes a direct statement of the
user's age with other information. Split it into atomic facts: each fact says exactly one thing and has its own
supporting quote copied verbatim from the user's words.

Memory entry: "{entry}"
User's words: "{quote}"

Reply with JSON only:
{{"facts": [{{"text": "...", "quote": "..."}}]}}"""
