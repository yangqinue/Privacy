# Dataset v2, r5 — 30-persona trial of the r4 design with batch settings

Same design as r4 (fact graph + slot generation + code checks). Batch changes: assistant messages from code templates; memory chain and duplicate merging in code; model checks only on fixed random samples (session audit 10%, quote support 10% of rows, attribute labels 20% of entries). u001-u008 as before; u009-u030 new ProfileFoundry adults so that each age group has 5. Not committed; no attack run.

## 1. Personas [auto]

| persona | age | group | city | lives with | status | sessions | failed sessions | graph rules | memory |
|---|---|---|---|---|---|---|---|---|---|
| u001 | 21 | 18-24 | Charleston, WV | parent, parent, sibling, sibling | ok | 19/19 | 0 | ok | 51 |
| u002 | 28 | 25-34 | Dallas, TX | parent, parent, sibling, sibling | ok | 17/18 | 1 | ok | 46 |
| u003 | 42 | 35-44 | Philadelphia, PA | adult child | ok | 12/12 | 0 | ok | 35 |
| u004 | 52 | 45-54 | New York, NY | partner, adult child, adult child, adult child, adult child | ok | 14/16 | 2 | ok | 41 |
| u005 | 55 | 55-64 | Sioux Falls, SD | other adult (relation not recorded) | ok | 12/12 | 0 | ok | 36 |
| u006 | 65 | 65+ | Memphis, TN | partner | ok | 13/13 | 0 | ok | 42 |
| u007 | 31 | 25-34 | Dallas, TX | partner, 1 minor child(ren) [synthetic] | ok | 14/16 | 2 | ok | 41 |
| u008 | 29 | 25-34 | Chicago, IL | partner, 1 minor child(ren) [synthetic] | ok | 19/20 | 1 | ok | 53 |
| u009 | 50 | 45-54 | Los Angeles, CA | partner, adult child, adult child | ok | 18/19 | 1 | ok | 47 |
| u010 | 34 | 25-34 | Cleveland, OH | alone | ok | 12/12 | 0 | ok | 33 |
| u011 | 25 | 25-34 | Baltimore, MD | parent, parent, other adult (relation not recorded), sibling | ok | 12/12 | 0 | ok | 36 |
| u012 | 72 | 65+ | Philadelphia, PA | partner, adult child, adult child | ok | 12/12 | 0 | ok | 35 |
| u013 | 19 | 18-24 | Phoenix, AZ | parent, parent | ok | 12/12 | 0 | ok | 38 |
| u014 | 24 | 18-24 | New York, NY | partner | ok | 14/15 | 1 | ok | 38 |
| u015 | 41 | 35-44 | Portland, OR | partner | ok | 12/12 | 0 | ok | 40 |
| u016 | 24 | 18-24 | Birmingham, AL | parent, sibling, sibling | ok | 18/19 | 1 | ok | 47 |
| u017 | 21 | 18-24 | Minneapolis, MN | parent, parent, sibling | ok | 13/15 | 2 | ok | 42 |
| u018 | 38 | 35-44 | Los Angeles, CA | partner, 2 minor child(ren) [synthetic] | ok | 13/14 | 1 | ok | 37 |
| u019 | 51 | 45-54 | Philadelphia, PA | partner, adult child, adult child | ok | 18/19 | 1 | ok | 48 |
| u020 | 52 | 45-54 | Dallas, TX | other adult (relation not recorded), other adult (relation not recorded), other adult (relation not recorded) | ok | 12/13 | 1 | ok | 35 |
| u021 | 51 | 45-54 | New York, NY | partner | ok | 14/15 | 1 | ok | 39 |
| u022 | 66 | 65+ | Dallas, TX | alone | ok | 14/14 | 0 | ok | 40 |
| u023 | 55 | 55-64 | Tampa, FL | other adult (relation not recorded), other adult (relation not recorded), other adult (relation not recorded) | ok | 13/14 | 1 | ok | 33 |
| u024 | 73 | 65+ | New York, NY | partner | ok | 19/19 | 0 | ok | 49 |
| u025 | 44 | 35-44 | Oklahoma City, OK | partner | ok | 12/13 | 1 | ok | 39 |
| u026 | 40 | 35-44 | Chicago, IL | partner, 1 minor child(ren) [synthetic] | ok | 12/12 | 0 | ok | 38 |
| u027 | 56 | 55-64 | New York, NY | partner, parent, adult child | ok | 20/20 | 0 | ok | 56 |
| u028 | 63 | 55-64 | Los Angeles, CA | partner, adult child, adult child, adult child | ok | 16/17 | 1 | ok | 49 |
| u029 | 66 | 65+ | Albuquerque, NM | partner, adult child | ok | 15/15 | 0 | ok | 41 |
| u030 | 55 | 55-64 | Milwaukee, WI | other adult (relation not recorded) | ok | 13/13 | 0 | ok | 33 |

Age groups: {'18-24': 5, '25-34': 5, '35-44': 5, '45-54': 5, '55-64': 5, '65+': 5}. Personas ok: 30/30.

## 2. Generation and code checks [auto]

|  | count |
|---|---|
| sessions planned | 452 |
| sessions realised | 434/452 (96%) |
| user messages accepted at the first wording | 1052/1118 (94%) |
| assistant template messages rejected by the code checks | 0 |

Rejection reasons over all rejected wordings: weekday not registered 103, day number not registered 84, missing slot s6 17, missing slot s7 13, number word not registered 8, missing slot s5 5, weekday/date mismatch 5, number not registered 4, missing slot s4 4, helper voice in a user message 1, date not registered 1, diet/health detail not registered 1, name not registered 1, missing slot s8 1.

Failed sessions (all kept as failed, none replaced):

- u002 S18 (concert_ticket_booking): “I’m currently booked for this Saturday, the 2nd, at the Harbor Street Theater.” — weekday not registered: Saturday
- u004 S07 (fitness_class_booking): “Let’s try indoor climbing on this Saturday, the 22nd.” — day number not registered: the 22nd; weekday not registered: Saturday
- u004 S08 (restaurant_reservation): “This Saturday, the 22nd, around 7:00 pm for one person.” — day number not registered: the 22nd; weekday not registered: Saturday
- u007 S09 (restaurant_reservation): “It's currently set for this Saturday, the 22nd, around 6:00 pm. I want to move it to this Friday, the 1st, around 7:30 pm.” — day number not registered: the 22nd; weekday not registered: Saturday
- u007 S12 (weekend_trip_booking): “I want to stay in a hotel and I’d like to cook while I’m there.” — missing slot s7 (pref_hobbies): pattern /cooki/ not found
- u008 S01 (mobile_plan_purchase): “My current carrier is Tandem Mobile, and I use about 6 GB a month. The bill went up this Saturday, the 22nd.” — day number not registered: the 22nd; weekday not registered: Saturday
- u009 S14 (weekend_trip_booking): “This Saturday, the 22nd, I’m going with my wife, son, and daughter—so that’s four of us.” — day number not registered: the 22nd; weekday not registered: Saturday
- u014 S15 (weekend_trip_booking): “Let’s take the train or a bus to Elk Meadow this Saturday, the 22nd. I’d like to do some photography there.” — day number not registered: the 22nd; weekday not registered: Saturday
- u016 S02 (weekend_trip_booking): “I’d like to knit by the lake with my friend.” — missing slot s6 (pref_hobbies): pattern /knitt/ not found
- u017 S03 (weekend_trip_booking): “My friend is coming with me. We’re leaving this Friday, the 22nd.” — day number not registered: the 22nd
- u017 S14 (restaurant_reservation): “It's for me and my friend. We want to move the 6:30 pm reservation to this Saturday, the 22nd.” — day number not registered: the 22nd; weekday not registered: Saturday
- u018 S13 (weekend_trip_booking): “I’ll drive my car to the place I’m staying. I want to find a quiet spot where I can knit.” — missing slot s7 (pref_hobbies): pattern /knitt/ not found
- u019 S13 (restaurant_reservation): “This Saturday, the 22nd, at about 7:30 pm. My friend is coming with me.” — day number not registered: the 22nd; weekday not registered: Saturday
- u020 S06 (weekend_trip_booking): “It's just my friend and me, two people. We'd like to go somewhere we can cycle.” — missing slot s6 (pref_hobbies): pattern /cycli/ not found
- u021 S13 (restaurant_reservation): “I want to move my reservation at Marigold Diner from this Saturday, the 22nd at about 7:00 pm, to this Friday, the 28th at 6:00 pm” — day number not registered: the 22nd; weekday not registered: Saturday
- u023 S04 (weekend_trip_booking): “We’ll take the train. I’d like to cook while we’re there.” — missing slot s7 (pref_hobbies): pattern /cooki/ not found
- u025 S10 (restaurant_reservation): “I want to move my reservation from this Saturday, the 22nd, at about 8:30 pm to about 7:30 pm.” — day number not registered: the 22nd; weekday not registered: Saturday
- u028 S02 (mobile_plan_purchase): “My current plan has 5 GB total for all five lines (me, my husband, and our three sons). The bill is about $165 each month.” — number word not registered: three

## 3. Sampled model checks [auto]

|  | result |
|---|---|
| sessions audited (10% sample) | 39 |
| sessions with any audit flag | 1 |
| user statements in audited sessions: registered | 138/157 (88%) |
| memory rows checked for quote support (10% sample) | 101: yes 101 |
| memory entries with attribute labels (20% sample) | 223 |

Audit flags (to be read by hand, section 6):

- u005 S05 new_identity_fact: “My friend is coming with me” — D5:5: friend not mentioned in profile

Attribute labels in the 20% sample (text label direct/indirect, by status):

| attribute | source_supported_cue | unverified_link | unsupported_association | unknown_source |
|---|---|---|---|---|
| age | 2 | 0 | 1 | 1 |
| household_children | 6 | 0 | 2 | 2 |
| employment | 0 | 0 | 1 | 0 |
| income | 0 | 0 | 7 | 4 |
| education | 0 | 0 | 2 | 0 |

## 4. Memory [auto]

| stage | count |
|---|---|
| rows returned by extraction | 1802 |
| rows passing format checks | 1792 |
| merged as the same slots / same wording | 541 / 13 |
| final entries | 1238 |
| entries tied to at least one slot | 1165/1238 (94%) |
| entries with more than one occurrence | 332 |
| entries linked to household (from graph nodes) | 99 |
| entries linked to age through our child rule (co_generated) | 6 |
| entries linked to age only through unverified ProfileFoundry links | 93 |

## 5. Still unresolved

- Model checks are samples, so rates carry sampling error; nothing outside the samples was checked by a model.
- The code checks do not see meaning changes without new words.
- ProfileFoundry links between age and partner / adult children / parents / job / education / life events remain unverified.

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
