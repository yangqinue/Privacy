## 6. Human check of the fixed sample [manual]

Read: 60 sessions (2 per persona) and 150 memory entries (5 per persona) from `human_check_sample.md`, plus all 25
failed sessions and the one audit flag. Nothing was changed after reading.

**Sessions (60 read): no factual error found** — every date, weekday, person, place and number matches its slots.
Form problems: users repeat the date in every message (u014 S06, u021 S08); one template is ungrammatical ("How many
people the order is for is it for?", u016 S15); "a indoor climbing class"; the assistant sometimes asks for one thing
and the user answers another (u024 S02: asked seating, user gave music). Estimated factual error rate in sessions:
0/60 (95% upper bound about 5%).

**Memory (150 read): 5 entries wrong or overstated (≈3%)**
- u019 m034 "prefers concerts with seating" cites "Can you find ones that have 2 tickets available?" — wrong quote;
  the code chain still marks it registered because the entry text contains the slot's words.
- u022 m030 "sign up for a swimming class" — the quote says only "a fitness class".
- u027 m040 "lunch for two people" and u012 m012 "pilates at Summit Climb & Train" — part of the entry is not in
  the cited quote (it is in another message of the same session).
- u018 m025 "User is married" from "Coming are my wife" — a cue turned into an identity fact.
Also: requests repeated over sessions are merged into one entry ("User is traveling alone" ×4), which keeps the
frequency but not which trip; ~5% of entries are just the errand request and have no slot (basis unknown).
So the code chain checks that an entry's words match a slot, but not that the cited quote is the right one; the 10%
model sample (99/99 "yes") did not catch the four quote problems above.

**Failed sessions (25): 9 are errors of the code checks, 16 are real**
- Code-check errors: the hobby rule used the first five letters ("cooki", "knitt", "readi", "cycli"), so "cook",
  "knit", "read", "cycle" were rejected (7 sessions); "two sons", "three sons" were rejected as unregistered number
  words (2 sessions). 3 of the 4 failed personas (u012, u026, and u015 partly) lost sessions this way.
- Real: the model repeatedly writes "this Saturday, the 22nd" instead of the registered date (14 sessions; the
  re-wording prompt does not break this habit); a user leaves out who is on the phone plan (u012 S05); a date
  given as the bill date (u008 S01).

**Model audit sample:** 1 flag in 38 sessions ("my friend" as a new identity fact) — an audit error.

## 7. Fix of the four failed personas (after section 6)

Changes, applied to the code for all personas: hobby words matched by stem ("cook", "knit", "read", "cycl|bik", ...);
number words allowed when they count listed relatives ("my two sons"); on a retry, the dates of the message are
spelled out, or, if the message has no date, the model is told not to mention any day or date; retries use a higher
temperature. Memory: an entry counts as registered only if the cited quote itself contains the slot's words (6 of
1,225 entries in the 30 personas are now marked `quote_mismatch` instead).
Re-run: only u012, u013, u015, u026 (their first wordings are reused from cache, so their passing sessions did not
change); their previous state is kept in `before_fix/`. All four now realise 12/12 sessions; 30/30 personas ok.
The other 26 personas' sessions were not regenerated (their 14 failed sessions stay failed); memory was rebuilt for
all 30 with the new quote rule. Sections 1-6 above describe the state before this fix.
