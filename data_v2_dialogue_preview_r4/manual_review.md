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
