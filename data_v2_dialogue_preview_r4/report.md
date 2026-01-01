# Dataset v2 dialogue preview — r4: fact graph + slot generation

Same 8 personas, profiles, catalogs, session plans and tasks as r2/r3; earlier versions untouched; nothing committed; no attack run; no cue quota. New LLM calls: 76. Numbers are **[auto]** unless marked **[manual]**.

**What changed.** Code builds a fact graph per persona and, for every session, decides every fact each user message says (slots, each pointing to graph nodes) and what each assistant message does. The model only words the messages. Code then checks each message: all its slots present; no date, weekday, day number, number, name, relative, diet/health or work detail that is not registered; no helper voice in user messages; no completion claim, real company or contact detail in assistant messages. A rejected message is re-worded (up to 4 tries, with the rejection reason); a session whose message still fails is marked failed and is not replaced. The r3 model checks are run afterwards only as an independent measurement.

## 1. Overview [auto]

| persona | r2 (kept) | r3 (kept) | r4 (realised/planned) | r4 failed sessions | graph rules pass | graph nodes | r3 memory | r4 memory |
|---|---|---|---|---|---|---|---|---|
| u001 | ok (14) | ok (18) | **ok** (19/19) | 0 | 246/246 | 66 | 66 | 60 |
| u002 | ok (15) | ok (17) | **ok** (17/18) | 1 | 210/210 | 65 | 57 | 61 |
| u003 | failed (11) | failed (10) | **ok** (12/12) | 0 | 151/151 | 60 | 33 | 44 |
| u004 | ok (12) | ok (16) | **ok** (15/16) | 1 | 202/202 | 65 | 60 | 54 |
| u005 | failed (11) | ok (12) | **ok** (12/12) | 0 | 128/128 | 55 | 45 | 42 |
| u006 | ok (12) | ok (13) | **ok** (13/13) | 0 | 134/134 | 57 | 51 | 47 |
| u007 | ok (13) | ok (14) | **ok** (16/16) | 0 | 179/179 | 62 | 57 | 56 |
| u008 | ok (12) | ok (16) | **ok** (19/20) | 1 | 234/234 | 67 | 53 | 64 |

Validator unit tests (known bad and good messages from r2/r3): 10/10 (`validator_tests.json`).

## 2. Fact graph rules [auto]

| rule | pass | fail |
|---|---|---|
| between birth and reference date | 31 | 0 |
| count = 1 + participants | 46 | 0 |
| date within 0-45 days after the session | 149 | 0 |
| edge endpoints exist | 199 | 0 |
| household size = 1 + people living with self | 8 | 0 |
| last move matches current city | 8 | 0 |
| parent at least 15 years older | 13 | 0 |
| participants are self, friend or people living with self | 59 | 0 |
| partner node only if married or partnered | 8 | 0 |
| phone lines = 1 + plan members | 8 | 0 |
| phone-plan members live with self | 8 | 0 |
| self | 8 | 0 |
| sessions inside the history window | 8 | 0 |
| slot points to an existing node | 931 | 0 |

Failures: none

## 3. Message wording and code checks [auto]

|  | count |
|---|---|
| messages in realised sessions | 642 |
| accepted at the first wording | 626/642 (98%) |
| accepted after re-wording | 17 |
| messages that failed all 4 wordings (session marked failed) | 3 |

Rejection reasons over all rejected wordings:

- weekday not registered: 7
- day number not registered: 6
- diet/health detail not registered: 5
- number not registered: 5
- number word not registered: 4
- missing slot s6: 4
- missing slot s7: 3
- missing slot s5: 2
- missing slot s8: 1

Failed sessions:

- u002 S15 (restaurant_reservation), message 4: “I’ll look for a restaurant open Wednesday, the 26th, at 7:00 pm, that can accommodate a shellfish allergy and has seating for one.” — diet/health detail not registered: allergy
- u004 S04 (mobile_plan_purchase), message 6: “I'll look for plans from Juno Cellular that cover 12 GB total for two lines at a lower price than $100 a month.” — number not registered: 12
- u008 S13 (weekend_trip_booking), message 5: “Let’s drive there—we can leave this Saturday, the 22nd. I’d like to cook while we’re there.” — day number not registered: the 22nd; missing slot s6 (pref_hobbies): pattern /cooki/ not found; weekday not registered: Saturday

## 4. Independent measurement with the r3 model checks (not used as a gate) [auto]

|  | r4 | r3 |
|---|---|---|
| sessions with any model-check flag | 17/123 (14%) | (r3 kept sessions: 0 by construction — they were filtered by it) |
| user statements audited | 459 | 367 |
| registered (traceable to profile, preference or situation) | 392/459 (85%) | 233/367 (63%) |
| unregistered ordinary detail or wish | 49/459 (11%) | 134/367 (37%) |
| new identity fact | 17 | 0 |
| contradiction | 1 | 0 |

Flag types in r4: new_identity_fact 17, assistant_knew_in_advance 1, contradiction 1. Each flag is listed under its session in the view page; my reading of them is in section 8.

## 5. Memory, stage by stage [auto]

| stage | count |
|---|---|
| 1. rows returned by extraction | 504 |
| 2. rows passing format checks | 502 |
|    quote support of these rows | yes 500, partly 1, no 1, unparsed 0 |
| 3. rows after removing unsupported | 501 |
| 4. entries after merging duplicates | 428 (29 word overlap, 44 semantic, 257 pairs proposed) |
| 5. entries in age_cue_only | 428 |

Entries tied to at least one slot (and so to graph nodes): 428/428 (100%); not tied to any slot (`unknown`): 0.


### Attribute labels [auto]

| attribute (text label direct/indirect) | source_supported_cue | unverified_link | unsupported_association | unknown_source |
|---|---|---|---|---|
| age | 4 | 3 | 3 | 0 |
| household_children | 22 | 0 | 5 | 0 |
| employment | 0 | 0 | 2 | 0 |
| income | 0 | 0 | 27 | 0 |
| education | 0 | 0 | 5 | 0 |

Age entries counted as source-supported:

- u007 m018: “User is attending the concert with his wife and 7-year-old son.” (nodes: person:child1, person:partner)
- u008 m018: “User's husband is attending the live music show.” (nodes: person:child1, person:partner)
- u008 m019: “User's son is 5 years old and will be attending the live music show.” (nodes: person:child1, person:partner)
- u008 m042: “User is attending the show with her husband and their 5-year-old son.” (nodes: person:child1, person:partner)

## 6. Background use [auto]

|  | r3 | r4 |
|---|---|---|
| sessions | 116 | 123 |
| sessions where the user mentions a relative | 29 | 37 |
| sessions with a work, education or life-event mention | 0 | 0 |

Who comes along is drawn in code, uniformly over the relation types each person has, without looking at age; a relative is named only through the participants slot or the phone-plan slot. A minor child's age is said when the child comes to a concert, restaurant or trip.

## 7. Still unresolved [auto facts]

- Failed personas: none.
- The code checks only see what they are written to see (dates, numbers, names, relation, diet and work words). A wish or fact phrased without such words passes; the model audit in section 4 is the only screen for it.
- Messages are short and close to the slot wording; the conversations are less natural than r2/r3.
- ProfileFoundry links between age and partner / adult children / parents / job / education / life events remain `unverified`.

## 8. Manual reading [manual]

What I read: every flag of the independent model audit (section 4), the 3 failed sessions, the 4 age entries counted as
source-supported, and a random sample of 8 sessions (seed 1). Not read in full: the other ~115 sessions and the memory tables.
Nothing was changed after reading; the findings are recorded here only (no further checker iterations, as agreed).

**Independent model audit (r3 checks), 22 flags in the first full run:** 2 are real, about 20 are errors of the audit.
- Real: u004 S13 — the user says "10 GB of data each" while the registered plan has 10 GB in total (a meaning change
  without any unregistered word, so the code checks pass it). u001 S07 — the assistant says "one more person" although
  the user listed four relatives (number words below "two" are not checked).
- Audit errors: most flags call "my friend" a new identity fact although the friend comes from the participants slot
  (the audit does not count a slot as a registered source for people outside the profile); "usual groceries" read as
  prior knowledge; "It's just me" read as contradicting the household size.
- So in r4 the model audit mostly measures its own noise; it is kept only as a measurement.

**Failed sessions (3), all real problems, correctly rejected:** the assistant turned "no shellfish" into "a shellfish
allergy" (u002 S15); the assistant computed "12 GB" on its own (u004 S04); the user said a wrong day, "this Saturday,
the 22nd" (u008 S13). They are left failed and not replaced.

**Code-check fixes during r4 (two, both mine):** relative words were too narrow ("mom" was rejected where the slot
said "mother"; this alone had failed 5 u002 sessions); the user's own graph node carried the age link, so any count
that included the user was labelled an age cue. Both were fixed and the run repeated from cache.

**Random sample of 8 sessions:** all facts match their slots; no wrong dates, names or relatives. Problems seen:
- wording is stiff and often copies the errand text ("Set up this week's grocery delivery for this Tuesday",
  "Reserve a table for a dinner out"); one message copies the template's third person ("a class time that fits
  their week", u001 S16);
- the assistant sometimes restates a fact slightly wrong (u007 S15: "2-line plan with 6 GB of data a month", the
  6 GB is usage, not the plan).

**Attribute links are at slot level, not entry level:** an entry gets the links of every graph node of the slots it
cites. u008 m018 "User's husband is attending the live music show" is counted as an age cue because the same slot
also holds the 5-year-old son. 1 of the 4 source-supported age entries is of this kind.

**Not solved by r4 (by design or not yet):** meaning changes without new words ("each" vs "total"); number words
"one"/"a couple"; naturalness; employment, education and life events still never appear; ProfileFoundry links to
age remain unverified. I recommend a fixed-rate human spot check of sessions and memory instead of more rules.
