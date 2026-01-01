"""Templates added or changed for the repair version r3 (r2 templates stay in v2r2_templates.py, unchanged).

All templates here are ADDED by us (no upstream counterpart) except user_turn_request, which only changes how the
conversation so far is shown to the PersonaMem-derived user simulator of r2.
"""

# How the user simulator is shown the conversation in r3: one transcript, not role-flipped chat messages
# (role-flipped messages made the simulator answer in the assistant's voice in a few r2 sessions).
def user_turn_request(conv, last):
    if not conv:
        return "(The conversation starts.) Write the user's first message."
    lines = "\n".join(("User (you): " if t["role"] == "user" else "Chatbot: ") + t["content"] for t in conv)
    return ("Conversation so far:\n" + lines + "\n\nWrite the user's next message. You are the user, not the chatbot: "
            "do not offer to look things up and do not repeat the chatbot's words."
            + (" This is your last message in this conversation." if last else ""))


ASSISTANT_CHECK_PROMPT = """You are checking the ASSISTANT's messages in one simulated conversation between a user and
their personal AI assistant. Judge only what the assistant wrote. The user's messages are checked elsewhere.

WHAT THE ASSISTANT WAS GIVEN (it may use this freely; it has seen nothing else and has no tools):
{public_context}

CONVERSATION ({date}):
{conversation}

Report a problem only when one of these clearly applies, and quote the assistant's exact words:
- "assistant_knew_in_advance": the assistant asserts a fact ABOUT THE USER (their preference, diet, family, habit,
  location, plan, usage) that the user has not said earlier in this conversation and that is not in what the
  assistant was given.
- "assistant_claims_completion": the assistant says the action itself is already done: it has booked, reserved,
  ordered, changed, paid or confirmed with the provider.
- "assistant_invented_listing": the assistant states as real a specific thing it could not know: a named show,
  business, carrier, place or product that the user did not name, a price, an available time slot, a travel time or
  distance, a phone number or address.
- "role_swap": an assistant message is written as if the assistant were the customer (it states its own preferences
  or needs), or a user message is written as the helper (it offers to look things up or asks the questions the
  assistant should ask). For this type the quote may come from either speaker.

These are NOT problems; do not report them:
- saying it has noted, written down or understood something ("noted", "got it", "I'll note that");
- saying what it will do next ("I'll look for", "I'll check", "let me check", "I can help you add", "I'll let you
  know", "I'll confirm once", "I can proceed with that list");
- repeating or summarising what the user said, including names and numbers the user gave;
- asking a question, including asking for something the user could have said already;
- offering kinds of things to consider (unlimited data, a quiet hotel, driving or taking a train, a kids' menu)
  without presenting a specific named item, price or slot as real;
- not knowing something, or saying it cannot do something;
- using the date, calendar or home city it was given.

Reply with JSON only:
{{"problems": [{{"type": "...", "quote": "<exact words copied from the conversation>", "reason": "..."}}]}}"""


CLAIMS_PROMPT = """You are auditing the USER's messages in one simulated conversation between a user and their personal
AI assistant. Every statement the user makes has to come from somewhere that was registered before the conversation.

REGISTERED SOURCES (id: content). "profile.*" is the user's profile as of the conversation date, "pref.*" are
registered preferences, "ctx.*" is the situation of this errand fixed before the conversation:
{elements}

USER MESSAGES ({date}):
{messages}

Split the user's messages into the separate things they assert or ask for (facts about themselves or other people,
details of the errand, requirements and wishes). Skip greetings, thanks, plain questions and plain yes/no answers.
For each one give:
- "id": the message id, e.g. "D3:1";
- "quote": the exact words, copied from that message;
- "kind", one of:
    "registered"          – it is stated in, or follows directly from, the registered sources (give their ids);
    "unregistered_detail" – an ordinary detail or wish for this errand that is not in the registered sources
                            (a time, an item, a feature, a place, a price limit, a seating wish);
    "new_identity_fact"   – a fact about who the user is or about the people around them that is not in the
                            registered sources: age, family or household members, a relative's name, job or working
                            hours, education, a health condition or diet of the user or of a relative, or an
                            important life event (move, marriage, divorce, birth, new job, graduation, retirement);
    "contradiction"       – it contradicts a registered source;
- "elements": the ids of the registered sources that support it (empty unless kind is "registered");
- "reason": a few words.

Rules: relationship words that follow from the profile are registered ("my wife", "our kids" for children of any
age, "my parents"). A number of people that matches the registered participants or household is registered. A
relative's first name is registered only if it appears in the sources. Asking for something because of a registered
preference is registered. A diet or health need attributed to another person is a new_identity_fact unless it is in
the sources. Saying a different date or number than the registered one is a contradiction.

Reply with JSON only:
{{"claims": [{{"id": "D3:1", "quote": "...", "kind": "...", "elements": ["..."], "reason": "..."}}]}}"""


SUPPORT_PROMPT = """A personal AI assistant stored the MEMORY ENTRY below about its user after a conversation.

MEMORY ENTRY: "{entry}"
Stored scope: {scope}

EVIDENCE (the cited user message{plural}, each with the assistant message just before it):
{evidence}

AUDITED STATEMENTS in the cited user message{plural} (id: exact words):
{claims}

Answer three things.
1. supported: "yes" only if the user's words in the evidence say, or clearly confirm (for example "yes" to the
   assistant's question), everything the entry says. "partly" if the entry adds, generalises or changes anything
   (for example it turns a request for this occasion into a habit, or adds a reason the user did not give). "no" if
   the evidence does not say it.
2. scope: "stable" only if the user's own words present it as lasting (for example "I am", "I usually", "I always",
   "I can't eat"); otherwise "one_off".
3. statements: the ids of the audited statements whose content the entry records (possibly several; empty if none).

Reply with JSON only:
{{"supported": "yes" or "partly" or "no", "scope": "one_off" or "stable", "statements": ["c1"], "reason": "..."}}"""


PAIR_DUPLICATE_PROMPT = """Two memory entries about the same user, possibly from different days:

A: "{a}"
B: "{b}"

Do A and B record the same thing about the user, so that B could be folded into A as one more occurrence without
losing anything except the day it was said? Answer "yes" only if the content is the same (same fact, same preference,
or the same request with the same particulars). Answer "no" if B has any particular that A lacks (another date,
number of people, place, item, reason), or if they are merely about the same topic.

Reply with JSON only: {{"same": "yes" or "no"}}"""


REWRITE_PROMPT = """The message below was written by a user to their personal AI assistant about this errand: {errand}.
It recites more of the user's family details than a person would type for this errand.

Rewrite it so that it keeps only what the errand needs:
- keep how many people are involved and their relationship to the user (wife, kids, parents, ...);
- keep a child's age only if the child is under 18 and the age matters for this errand (seating, tickets, a
  family-friendly place);
- remove the ages of adults and the first names of relatives;
- change nothing else: same request, same dates, times, places, numbers and tone.

Message: "{text}"

Reply with JSON only: {{"text": "..."}}"""


CONTRADICTION_CONFIRM_PROMPT = """A checker says the user's words contradict something registered before the conversation.

Registered sources:
{elements}

User's words ({dia_id}): "{quote}"
Checker's reason: {reason}

Is it impossible for the user's words and the registered sources to both be true?
Answer "no" (compatible) when the user only offers a tentative alternative or asks a question ("maybe Saturday?"),
gives a date without its month or year, picks another day of the same registered weekend or week, or adds a wish the
sources say nothing about. Answer "yes" only for a real conflict: a different date, number, person, place or
preference than the registered one, stated as what the user wants or as a fact.

Reply with JSON only: {{"conflict": "yes" or "no"}}"""
