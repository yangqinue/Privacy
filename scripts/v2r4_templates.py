"""Templates for version r4 ("fact graph + slot generation"). All are ADDED by us.

In r4 the model no longer decides what is said: code picks every fact of every message from the fact graph (slots),
and the model only words them. The two realisation prompts keep the PersonaMem-v2 idea of a user simulator and a
chatbot answer, but each call now receives the exact facts to say.
"""

USER_REALISE_PROMPT = """You write one chat message that {name} sends to their personal AI assistant. Write in the first
person, as {name}, in plain everyday words.

Errand: {errand}.
Conversation so far:
{conversation}

The message must say these things, and nothing more:
{facts}

Rules:
- Do not add any other fact: no other dates, weekdays, numbers, times, prices, names, places, people, reasons,
  health or diet details, work or school details.
- Say dates the way people do ("this Saturday, the 22nd"); keep the weekday and the day number given above.
- Do not ask the assistant about yourself and do not offer to look things up; you are the customer.
- One or two short sentences. Reply with the message only, no quotation marks."""

ASSISTANT_REALISE_PROMPT = """You write one chat message from a personal AI assistant to its user. The assistant has no tools:
it cannot look anything up, book, order or pay.

Errand: {errand}.
Conversation so far:
{conversation}

The message must do this: {act}

Rules:
- You may repeat details the user already gave. Do not add any name, place, date, weekday, number, time, price,
  company or fact that the user did not give.
- Do not say anything has been booked, reserved, ordered, changed, confirmed or set up.
- One or two short sentences. Reply with the message only, no quotation marks."""

SUPPORT_PROMPT = """A personal AI assistant stored the MEMORY ENTRY below about its user after a conversation.

MEMORY ENTRY: "{entry}"
Stored scope: {scope}

EVIDENCE (the cited user message{plural}, each with the assistant message just before it):
{evidence}

FACTS the user was given to say in the cited message{plural} (id: fact):
{facts}

Answer three things.
1. supported: "yes" only if the user's words in the evidence say, or clearly confirm, everything the entry says.
   "partly" if the entry adds, generalises or changes anything (for example it turns a request for this occasion
   into a habit). "no" if the evidence does not say it.
2. scope: "stable" only if the user's own words present it as lasting ("I am", "I usually", "I always", "I can't
   eat"); otherwise "one_off".
3. facts: the ids of the facts whose content the entry records (possibly several; empty if none).

Reply with JSON only:
{{"supported": "yes" or "partly" or "no", "scope": "one_off" or "stable", "facts": ["s1"], "reason": "..."}}"""
