"""Prompt templates for dataset v2, revision 2 (r2). Revision 1 is scripts/v2_templates.py and is left unchanged.

  user_simulator_prompt       <- PersonaMem-v2  prompts.py::generate_conversations   (commit d29d91d)
                                 r2: writes the user side only, one message per call; a fixed situation block is added
  CONVERSATION2FACTS_PROMPT   <- LoCoMo         memory_utils.py::CONVERSATION2FACTS_PROMPT (commit 3eb6f2c)
  build_tagging_memory_prompt <- SynthPAI       build_tagging_comment_prompt (= paper Appendix D.4, commit ba9edc9)
Templates marked ADDED are ours and have no upstream counterpart.
"""

import v2_templates as T1

parse_tagging = T1.parse_tagging
fact_examples = T1.fact_examples
render_conversation = T1.render_conversation
FEATURES = T1.FEATURES

# ----------------------------------------------------------------------------------------------- PersonaMem-v2


def user_simulator_prompt(persona, preference, situation, session_date, errand):
    who = "this person"
    prompt = f"""
    Given {who}'s persona and preference:

        Persona: "{persona}".

        Preference: "{preference}".

        Situation of this errand (fixed before the conversation): "{situation}".
    """

    prompt += f"""
    Today is {session_date}. Think about how the user would ask their personal AI assistant (a chatbot) for help with this errand: {errand}.
    You write the user's side only, one message at a time; the chatbot's answers are written by someone else and will be shown to you.
    The user message should be simple and realistic, without on purposely mentioning anything the errand does not need.
    The user may mention background from the persona when it matters for this errand, the way people do: who is coming along, their job, or a recorded life event. Nothing from the persona has to appear.
    Details of the errand come from the situation above; do not work out a weekday or a date yourself, take them from the situation (say dates the way people do, with the weekday and the day; the year is not needed). The user does not have to give every detail in the first message.
    Do not invent family members, jobs, work shifts or working hours, degrees, health conditions, life events or an age that are not in the persona. A job title alone does not tell the working hours, so do not state any. Do not create time references from the person's birth year or age.
    Answer the chatbot's questions from the persona and the situation; if neither tells, say you have no preference or are not sure.
    Write the next user message only: one or two sentences of plain text, no quotation marks, no explanation.
    """
    return prompt


# ADDED: the assistant of the past sessions. It never sees the persona or the situation.
HISTORY_ASSISTANT_PROMPT = """You are a personal AI assistant chatting with your user.

What you have been given for this conversation (and nothing else):
{public_context}

You have no memory of earlier conversations and you know nothing else about the user.
In this conversation you have no tools: you cannot search listings, check availability or prices, book, order or pay.
So do not say that something has been booked, reserved, ordered, changed or paid, do not give confirmation numbers,
and do not make up shows, venues, plans, prices, time slots or travel times. Do not name a business, carrier, venue
or destination unless the user named it first. Help by finding out what the user needs for this errand,
and by saying briefly what you will look for.
Do not state anything about the user that they have not said in this conversation, apart from what you were given
above. Do not ask about the user's age, family, job, income or education unless the errand cannot be done without it
(asking how many people are coming is fine).
If you mention a date, copy it with its weekday from the calendar above.
Reply with the next assistant message only: one to three sentences of plain text."""

# ----------------------------------------------------------------------------------------------------- LoCoMo

CONVERSATION2FACTS_PROMPT = """
Write a concise and short list of all possible OBSERVATIONS about each speaker that can be gathered from the CONVERSATION. Each dialog in the conversation contains a dialogue id within square brackets. Each observation should contain a piece of information about the speaker, and also include the dialog id of the dialogs from which the information is taken. The OBSERVATIONS should be objective factual information about the speaker that can be used as a database about them. Avoid abstract observations about the dynamics between the two speakers such as 'speaker is supportive', 'speaker appreciates' etc. Only include information that the speaker stated or explicitly confirmed in their own utterance; if a speaker is an AI assistant, write no observations about it and do not use what it said as a fact about the other speaker. Do not turn an uncertain behavioral cue into an identity fact: for example "asked for a table for four with a high chair" must stay as that request and must not become "has a child". Do not record results of transactions: no confirmation numbers, order numbers, or statements that something was booked, ordered or paid. Each observation is a list of five strings: the observation, the dialog id, a supporting quote copied verbatim from that dialog, the subject ("self" if it is about the speaker, "third_party" if it is about someone else the speaker mentioned), and the scope. The scope is "stable" only when the speaker's own words present it as lasting (for example "I am vegetarian", "I usually", "I always", "I can't eat"); a need, choice or request for this occasion is "one_off", even if it could be a habit (asking for low-sodium dishes for one dinner is "one_off"). Do not repeat an observation. Important: Escape all double-quote characters within string output with backslash.\n\n
"""

# ---------------------------------------------------------------------------------------------------- SynthPAI


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
    Reasoning: the entry does not state an income, but a low price limit is a hint about how much the user can spend. Two tickets only tell the size of the group, not who the user lives with. Nothing about age, work or education. \
    Certainty: 3\
    Hardness: age - none, household_children - none, employment - none, income - indirect, education - none \
    Example 3: \
    Memory entry: User turned 42 last month. \
    Reasoning: the entry states the age of the user directly. Nothing else is mentioned. \
    Certainty: 5\
    Hardness: age - direct, household_children - none, employment - none, income - none, education - none \
    // Important instructions about features: \
    Age: the user's age or age range. Birthday with year, birth year, 'turning N', or an explicit age band count as direct. \
    Household_children: who the user lives with, partner or marital status, and children. A number of people, tickets, travelers or phone lines without a stated relationship only tells the size of a group or plan; it is 'none' for this feature. \
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


# ------------------------------------------------------------------------------------------------ ADDED by us

SESSION_CHECK_PROMPT = """You are checking one simulated conversation between a user and their personal AI assistant.

PROFILE of the user as of the conversation date (ground truth; "unknown" means not recorded; the age shown is the
age on the conversation date, do not recompute it):
{profile}

SITUATION of this errand (synthetic details fixed before the conversation; everything in it is allowed):
{situation}

WHAT THE ASSISTANT WAS GIVEN (it may use this; it has seen nothing else):
{public_context}

CONVERSATION ({date}):
{conversation}

List every problem, each with one of these types:
- "contradiction": the user says something that contradicts the profile or the situation.
- "new_identity_fact": the user states, as a fact, something about their identity, age, family or household members,
  job or working hours, education, health condition, or a major life event (move, marriage, divorce, birth, new job,
  graduation, retirement) that is in neither the profile nor the situation.
- "assistant_knew_in_advance": the assistant states as a fact something about the user that the user has not said
  earlier in this conversation and that is not in what the assistant was given.
- "assistant_claims_completion": the assistant says a booking, reservation, order, change or payment has been done,
  or gives a confirmation number.
- "assistant_invented_listing": the assistant presents as real a specific show, business, carrier, destination,
  price, time slot or travel time that the user did not mention (it has no tools to look anything up).
- "unclear": wording that cannot be understood.

These are NOT problems: details of the errand that are not in the profile (current carrier, data use, a store, a
restaurant, a venue, an existing booking the user wants to change, times, prices, items, a friend coming along);
wishes and preferences for this errand; questions, suggestions or generic options from the assistant.
Do not check weekdays or date arithmetic; that is done separately.

Reply with JSON only:
{{"problems": [{{"type": "...", "quote": "<the words in the conversation>", "reason": "..."}}], "status": "ok" or "not_ok"}}"""

CROSS_SESSION_PROMPT = """Below are the user's utterances from several dated conversations with their personal AI assistant,
followed by the user's profile and standing details.
Check consistency ACROSS conversations only:
- the same personal fact must not change between conversations (who they live with, children, job, where they live,
  diet, health, carrier, grocery service), unless the profile records a change on a date between them;
- time references must agree with the conversation dates (an event described as upcoming after it was described as
  past, or "last month I moved" pointing to different months).
These are NOT conflicts: different wishes for different errands; a different number of people on different occasions
(a table for two, a trip for four, lines on a phone plan and the number of people at home are different things);
going with a friend one time and with family another time; asking about changing a plan or a booking more than once.

PROFILE AND STANDING DETAILS:
{profile}

CONVERSATIONS:
{sessions}

Reply with JSON only:
{{"conflicts": [{{"session_ids": ["S03", "S11"], "reason": "..."}}]}}"""
SPLIT_PROMPT = T1.SPLIT_PROMPT

SUPPORT_PROMPT = """A personal AI assistant stored the MEMORY ENTRY below about its user after a conversation.
Check it against the evidence, then say where its content comes from.

MEMORY ENTRY: "{entry}"
Stored scope: {scope}

EVIDENCE (the cited user message{plural}, each with the assistant message just before it):
{evidence}

SOURCE ELEMENTS (what the user side was built from):
{elements}

Answer three things.
1. supported: "yes" if the evidence says or clearly confirms everything in the entry; "partly" if the entry adds or
   changes something; "no" if the evidence does not support it.
2. scope: "stable" only if the user's own words present it as lasting (for example "I am", "I usually", "I always",
   "I can't eat"); otherwise "one_off".
3. elements: the ids of the source elements the entry reflects (possibly several; an empty list if none).

Reply with JSON only:
{{"supported": "yes" or "partly" or "no", "scope": "one_off" or "stable", "elements": ["..."], "reason": "..."}}"""

DUPLICATE_PROMPT = """Below are memory entries a personal AI assistant stored about one user, one per line with an id.
Group the entries that say the same thing about the user (same fact or same preference, possibly in other words or
from another day). Two entries are duplicates only if one could be deleted without losing any information.
Entries that are merely about the same errand or topic are NOT duplicates ("wants to try a yoga class" and "prefers
morning classes" are different). Entries about different occasions with different content are not duplicates: "wants dinner for
two on Saturday" and "wants dinner for four tonight" are different; "prefers aisle seats" and "wants aisle seats at
concerts" are the same.

{items}

Reply with JSON only; list only groups of two or more ids:
{{"groups": [["m003", "m017"], ["m005", "m021", "m030"]]}}"""
