# r5 human-check sample (2 sessions and 5 memory entries per persona, fixed seed)


## u001

**u001 S04 concert_ticket_booking** — slots: what you want: ask which upcoming concerts in town would sui | the day: Sunday, 23 November (say the weekday and the day nu | seating: you prefer seated venues over standing | a time preference: you prefer morning activities | who is coming besides you: your father, your mother, your br | how many tickets: 5
- User: Looking for upcoming concerts in town that would suit me and have seats available on Sunday, the 23rd of November.
- Assistant: Thanks. How many tickets is it for?
- User: I want seated venues, not standing. It's for 5 people.
- Assistant: Got it. Who will be coming with you?
- User: It's for five people: my dad, my mom, my brother, my sister, and me. We prefer morning activities.
- Assistant: Here is what I'll look for: Sunday, the 23rd; preferring seated venues over standing; preferring morning activities; with your father, your mother, your brother, your sister; for 5 tickets.
**u001 S07 weekend_trip_booking** — slots: what you want: pick a destination for a short getaway and ch | the day: Friday, 13 February (say the weekday and the day nu | the day: Sunday, 15 February (say the weekday and the day nu | how you would travel: by train or bus | something you would like to do there: photography | who is coming besides you: your father, your mother, your br | how many travellers: 5
- User: Hey, I need you to pick a destination for a short getaway and check transport options. I want to leave on Friday, the 13th of February, and return on Sunday, the 15th.
- Assistant: Okay. How would you like to travel?
- User: I’d like to travel by train. Coming with me are my dad, mom, brother, and sister.
- Assistant: Thanks. Anything you'd like to do there?
- User: I want to take some great photos while we're there. There are five of us traveling.
- Assistant: Here is what I'll look for: Friday, the 13th; Sunday, the 15th; by train or bus; photography; with your father, your mother, your brother, your sister; for 5 travellers.
- memory m010 ×1 [registered; -]: “User prefers an afternoon delivery slot.” ← “Afternoon slot works for me.”
- memory m021 ×2 [registered; person:self]: “User needs only one ticket.” ← “need one ticket”
- memory m039 ×1 [registered; -]: “User is looking for a vacation rental for the trip.” ← “I want a vacation rental for Friday, the 17th through Sunday, the 19th.”
- memory m042 ×1 [registered; -]: “User wants to stay in a cabin during the trip.” ← “We’ll travel by car, and we want to stay in a cabin.”
- memory m047 ×1 [registered; fact:lines, fact:plan_data]: “User is on an unlimited data plan with one line.” ← “My current plan is unlimited data, and it's just one line.”

## u002

**u002 S16 weekend_trip_booking** — slots: what you want: pick a destination for a short getaway and ch | the day: Friday, 25 September (say the weekday and the day n | the day: Sunday, 27 September (say the weekday and the day n | where you are thinking of going: Elk Meadow | how you would travel: by car | how many travellers: 1
- User: Hi, I want to plan a short getaway from Friday, the 25th of September, to Sunday, the 27th. I’d like to pick a destination and check transport options by car.
- Assistant: Got it. Where are you thinking of going?
- User: I’m thinking of going to Elk Meadow for the weekend. Just me, so I need to check transport options by car.
- Assistant: Here is what I'll look for: Friday, the 25th; Sunday, the 27th; going to Elk Meadow; by car; for 1 traveller.
**u002 S12 mobile_plan_purchase** — slots: what you want: compare mobile phone plans and pick a cheaper | your current carrier: Beacon Wireless | your current plan's data: 10 GB in total for the whole plan  | how much data you use: about 3 GB a month | your monthly bill: about $170 | how many lines on the plan: 5 (you and your mother, your fat | why: calls drop at home sometimes
- User: I need you to compare mobile phone plans and help me pick a cheaper or better one.
- Assistant: Sure. How many lines on the plan is it for?
- User: Our current plan has 10 GB total for all 5 lines—me, my mom, dad, brother, and sister. I use about 3 GB a month.
- Assistant: Thanks. How much do you pay each month now?
- User: We’re with Beacon Wireless now, and our monthly bill is about $170. I’ve been having some dropped calls at home sometimes.
- Assistant: Here is what I'll look for: currently with Beacon Wireless; current plan 10 GB; about 3 GB used a month; about $170 a month now; for 5 lines; calls drop at home sometimes.
- memory m020 ×1 [registered; catalog:weekend_destinations:d3]: “User is traveling to Stonebridge.” ← “I’m thinking of going to Stonebridge”
- memory m021 ×4 [registered; person:self]: “User is traveling alone.” ← “traveling alone”
- memory m018 ×4 [registered; person:friend]: “User is traveling with a friend.” ← “my friend is coming with me”
- memory m042 ×1 [registered; -]: “User plans to travel by car.” ← “I’d like to pick a destination and check transport options by car”
- memory m016 ×2 [registered; pref:hobbies]: “User wants to go fishing during the trip.” ← “I’d like to go fishing while we’re there.”

## u003

**u003 S05 mobile_plan_purchase** — slots: what you want: check whether to change your current phone pl | your current carrier: Northwind Mobile | your current plan's data: 15 GB in total for the whole plan  | how much data you use: about 14 GB a month | your monthly bill: about $100 | how many lines on the plan: 2 (you and your daughter) | why: the bill went up recently
- User: I want to check whether to change my current phone plan. I'm with Northwind Mobile and I use about 14 GB a month.
- Assistant: Okay. What makes you want to change?
- User: The bill went up recently, and we’ve got two lines on the plan — mine and my daughter’s.
- Assistant: Okay. How much do you pay each month now?
- User: Our current plan has 15 GB total for both lines, and we're paying about $100 a month.
- Assistant: Here is what I'll look for: currently with Northwind Mobile; current plan 15 GB; about 14 GB used a month; about $100 a month now; for 2 lines; the bill went up recently.
**u003 S07 concert_ticket_booking** — slots: what you want: ask which upcoming concerts in town would sui | the day: Sunday, 1 March (say the weekday and the day number | seating: you prefer aisle seats | who is coming besides you: your daughter | how many tickets: 2
- User: Looking for upcoming concerts in town that would suit us and hold two seats for Sunday, the 1st of March. My daughter is coming with me.
- Assistant: Okay. Any seating preference?
- User: Aisle seats are better for us.
- Assistant: Here is what I'll look for: Sunday, the 1st; preferring aisle seats; with your daughter; for 2 tickets.
- memory m007 ×1 [registered; catalog:weekend_destinations:d2]: “User wants to go on a short getaway to Pine Hollow from Friday, the 5th of December to Sunday, the 7th of December.” ← “I want to pick a destination for a short getaway and check transport options. I’m thinking of going to Pine Hollow from Friday, the 5th of December to Sunday, the 7th of December.”
- memory m008 ×2 [registered; -]: “User wants to travel by train for this trip.” ← “I’d like to travel by train.”
- memory m022 ×1 [registered; -]: “User is available for the class on Saturday, the 14th, and Wednesday, the 18th.” ← “I'm available this Saturday, the 14th, and this Wednesday, the 18th.”
- memory m019 ×1 [registered; fact:plan_data]: “User's current plan includes 15 GB of data for both lines.” ← “Our current plan has 15 GB total for both lines”
- memory m032 ×1 [registered; -]: “User wants to reserve a place for a weekend lunch on Sunday, the 4th of October.” ← “Find a place for a weekend lunch and reserve it. I want it on Sunday, the 4th of October.”

## u004

**u004 S04 mobile_plan_purchase** — slots: what you want: check whether to change your current phone pl | your current carrier: Juno Cellular | your current plan's data: 10 GB in total for the whole plan  | how much data you use: about 6 GB a month | your monthly bill: about $100 | how many lines on the plan: 2 (you and your wife) | why: you want to pay less
- User: I want to check whether I should change my current phone plan. My plan has 10 GB of data total for the whole plan, and I pay about $100 a month.
- Assistant: Thanks. Which carrier are you with now?
- User: I'm with Juno Cellular, and the plan has two lines — mine and my wife's.
- Assistant: Got it. How much data do you use in a month?
- User: I use about 6 GB a month, so I'm wondering if there's a cheaper plan that would still work for us.
- Assistant: Here is what I'll look for: currently with Juno Cellular; current plan 10 GB; about 6 GB used a month; about $100 a month now; for 2 lines; you want to pay less.
**u004 S11 mobile_plan_purchase** — slots: what you want: check whether to change your current phone pl | your current carrier: Juno Cellular | your current plan's data: 10 GB in total for the whole plan  | how much data you use: about 6 GB a month | your monthly bill: about $100 | how many lines on the plan: 2 (you and your wife) | why: the bill went up recently
- User: Hey, I want to check whether I should change my current phone plan. My plan has 10 GB of data total for the whole plan.
- Assistant: Okay. How much do you pay each month now?
- User: We pay about $100 a month for the two of us—me and my wife—and the bill went up recently.
- Assistant: Got it. Which carrier are you with now?
- User: We're with Juno Cellular, and I use about 6 GB a month.
- Assistant: Here is what I'll look for: currently with Juno Cellular; current plan 10 GB; about 6 GB used a month; about $100 a month now; for 2 lines; the bill went up recently.
- memory m028 ×1 [registered; catalog:gyms:g2]: “User has specified Ironworks Gym as the location for the indoor climbing class.” ← “Ironworks Gym.”
- memory m014 ×3 [registered; fact:carrier]: “User is with Juno Cellular.” ← “I'm with Juno Cellular”
- memory m013 ×2 [registered; fact:monthly_bill_usd]: “User pays about $100 a month for their phone plan.” ← “I pay about $100 a month”
- memory m004 ×2 [registered; pref:hobbies]: “User is looking for a place to stay that has woodworking.” ← “I want to find a place that has woodworking.”
- memory m031 ×2 [registered; pref:music]: “User prefers R&B or video game soundtrack music.” ← “R&B or video game soundtrack stuff is what I’m into.”

## u005

**u005 S07 mobile_plan_purchase** — slots: what you want: compare mobile phone plans and pick a cheaper | your current carrier: Northwind Mobile | your current plan's data: 10 GB | how much data you use: about 14 GB a month | your monthly bill: about $65 | how many lines on the plan: 1 | why: calls drop at home sometimes
- User: I want to compare mobile phone plans and pick a cheaper or better one. I'm currently with Northwind Mobile.
- Assistant: Okay. How much data does your current plan have?
- User: My current plan has 10 GB of data and is just one line. I'm looking to switch because calls drop at home sometimes.
- Assistant: Thanks. How much data do you use in a month?
- User: I use about 14 GB a month and my bill is around $65.
- Assistant: Here is what I'll look for: currently with Northwind Mobile; current plan 10 GB; about 14 GB used a month; about $65 a month now; for 1 line; calls drop at home sometimes.
**u005 S12 mobile_plan_purchase** — slots: what you want: compare mobile phone plans and pick a cheaper | your current carrier: Northwind Mobile | your current plan's data: 10 GB | how much data you use: about 14 GB a month | your monthly bill: about $65 | how many lines on the plan: 1 | why: the bill went up recently
- User: I want to compare mobile phone plans and pick a cheaper or better one. I'm with Northwind Mobile and have 1 line on my plan.
- Assistant: Okay. How much data do you use in a month?
- User: My current plan is 10 GB. I use about 14 GB a month.
- Assistant: Sure. What makes you want to change?
- User: My monthly bill is about $65, and the bill went up recently.
- Assistant: Here is what I'll look for: currently with Northwind Mobile; current plan 10 GB; about 14 GB used a month; about $65 a month now; for 1 line; the bill went up recently.
- memory m017 ×2 [registered; fact:grocery_service]: “User uses DailyCrate for grocery orders.” ← “I use DailyCrate.”
- memory m006 ×4 [registered; person:friend]: “User will be attending the class with a friend.” ← “My friend is coming with me.”
- memory m028 ×1 [registered; -]: “User wants to reserve a table for 12:30 pm on Saturday, the 4th.” ← “How about 12:30 pm on this Saturday, the 4th?”
- memory m022 ×1 [registered; fact:monthly_bill_usd]: “User's current monthly bill is around $65.” ← “my bill is around $65.”
- memory m012 ×1 [registered; pref:hobbies]: “User wants to go rock climbing at the destination.” ← “We want to go rock climbing there.”

## u006

**u006 S01 fitness_class_booking** — slots: what you want: sign up for a fitness class or a class pack a | the class you want to try: spin | the gym: Riverbend Yoga | the day: Wednesday, 8 October (say the weekday and the day n | the day: Monday, 13 October (say the weekday and the day num | a time preference: you enjoy late-night events | who is coming besides you: your husband
- User: Sign me up for a fitness class or a class pack at a local gym. I want to start this Wednesday, the 8th, and maybe again this Monday, the 13th.
- Assistant: Got it. Who will be coming with you?
- User: I like late-night classes. My husband is coming with me.
- Assistant: Got it. Which class would you like to try?
- User: Let’s do spin at Riverbend Yoga. I want the 8th and the 13th.
- Assistant: Here is what I'll look for: a spin class; at Riverbend Yoga; Wednesday, the 8th; Monday, the 13th; enjoying late-night events; with your husband.
**u006 S04 mobile_plan_purchase** — slots: what you want: compare mobile phone plans and pick a cheaper | your current carrier: Tandem Mobile | your current plan's data: 10 GB | how much data you use: about 6 GB a month | your monthly bill: about $75 | how many lines on the plan: 1 | why: the bill went up recently
- User: I need you to compare mobile phone plans and help me pick a cheaper or better one.
- Assistant: Sure. How much data does your current plan have?
- User: I'm with Tandem Mobile now, on a 10 GB plan with just one line.
- Assistant: Got it. What makes you want to change?
- User: I use about 6 GB a month, and my bill went up to around $75 recently, so I want to see if there's a better or cheaper option.
- Assistant: Here is what I'll look for: currently with Tandem Mobile; current plan 10 GB; about 6 GB used a month; about $75 a month now; for 1 line; the bill went up recently.
- memory m023 ×1 [registered; fact:carrier]: “User is currently with Tandem Mobile.” ← “I'm with Tandem Mobile”
- memory m025 ×2 [registered; fact:grocery_service]: “User specified to use PantryRun for the grocery delivery.” ← “Use PantryRun for the delivery.”
- memory m008 ×1 [registered; catalog:restaurants:r5]: “User's reservation is at Saffron Door for Friday, the 12th, at about 6:00 pm.” ← “The reservation is at Saffron Door for this Friday, the 12th, at about 6:00 pm.”
- memory m016 ×1 [registered; fact:monthly_bill_usd]: “User's current bill is around $75 per month.” ← “my bill went up to around $75 recently”
- memory m027 ×1 [registered; pref:music]: “User is looking for a concert ticket for Saturday, the 1st, for either a hip-hop or classical event.” ← “what upcoming hip-hop or classical concerts are happening this Saturday, the 1st”

## u007

**u007 S08 fitness_class_booking** — slots: what you want: find a class time that fits your week and boo | the class you want to try: yoga | the day: Wednesday, 29 April (say the weekday and the day nu | the day: Saturday, 2 May (say the weekday and the day number | a time preference: you prefer morning activities | who is coming besides you: your wife
- User: Hey, I want to find a class time that fits my week and book a trial session. I'm free on Wednesday, the 29th of April, and Saturday, the 2nd of May, and I prefer morning activities. My wife will be coming with me.
- Assistant: Sure. Which class would you like to try?
- User: Let me try yoga on Saturday, the 2nd. Can you book a morning session for me and my wife?
- Assistant: Here is what I'll look for: a yoga class; Wednesday, the 29th; Saturday, the 2nd; preferring morning activities; with your wife.
**u007 S06 mobile_plan_purchase** — slots: what you want: compare mobile phone plans and pick a cheaper | your current carrier: Beacon Wireless | your current plan's data: 10 GB in total for the whole plan  | how much data you use: about 6 GB a month | your monthly bill: about $90 | how many lines on the plan: 2 (you and your wife) | why: you want to pay less
- User: I want to compare mobile phone plans and pick a cheaper or better one. Can you help me with that?
- Assistant: Okay. How many lines on the plan is it for?
- User: We're with Beacon Wireless, and we have two lines — mine and my wife's. We're looking to pay less.
- Assistant: Got it. How much data do you use in a month?
- User: Our current plan has 10 GB total for both lines, and we use about 6 GB a month between us. We’re paying around $90 a month right now.
- Assistant: Here is what I'll look for: currently with Beacon Wireless; current plan 10 GB; about 6 GB used a month; about $90 a month now; for 2 lines; you want to pay less.
- memory m011 ×3 [registered; fact:carrier]: “User is with Beacon Wireless.” ← “We’re with Beacon Wireless.”
- memory m025 ×2 [registered; fact:monthly_bill_usd]: “User is currently paying around $90 a month for their plan.” ← “We’re paying around $90 a month right now”
- memory m024 ×2 [registered; fact:plan_data]: “User's current plan has 10 GB of data for both lines.” ← “Our current plan has 10 GB total for both lines”
- memory m027 ×1 [registered; -]: “User wants to book tickets for a live music show on Friday, the 17th.” ← “I want to find and book tickets for a live music show this Friday, the 17th.”
- memory m008 ×4 [registered; pref:schedule]: “User prefers morning classes before the day gets busy.” ← “Morning works best for me — early classes, before the day gets busy.”

## u008

**u008 S05 concert_ticket_booking** — slots: what you want: find and book tickets for a live music show o | the day: Sunday, 21 December (say the weekday and the day nu | the kind of music: classical or hip-hop | who is coming besides you: your husband, your 5-year-old son | how many tickets: 3
- User: Find and book tickets for a live music show on Sunday, the 21st of December.
- Assistant: Thanks. What kind of music do you like?
- User: I want classical or hip-hop. Need 3 tickets for Sunday, the 21st.
- Assistant: Thanks. Who will be coming with you?
- User: My husband and my 5-year-old son will be coming with me.
- Assistant: Here is what I'll look for: Sunday, the 21st; classical or hip-hop; with your husband, your 5-year-old son; for 3 tickets.
**u008 S13 weekend_trip_booking** — slots: what you want: pick a destination for a short getaway and ch | the day: Friday, 3 July (say the weekday and the day number, | the day: Sunday, 5 July (say the weekday and the day number, | where you are thinking of going: Port Alder | how you would travel: by car | something you would like to do there: cooking | who is coming besides you: your friend | how many travellers: 2
- User: Hey, I want to plan a short getaway for Friday, the 3rd of July, and come back Sunday, the 5th. My friend is coming too. Can you help pick a destination and check transport options?
- Assistant: Thanks. Where are you thinking of going?
- User: I was thinking of going to Port Alder. It’s just me and my friend, so two people total.
- Assistant: Sure. How would you like to travel?
- User: Let’s drive to Port Alder—we can leave from here on Friday the 3rd and come back Sunday the 5th. I’d like to try some cooking there.
- Assistant: Here is what I'll look for: Friday, the 3rd; Sunday, the 5th; going to Port Alder; by car; cooking; with your friend; for 2 travellers.
- memory m005 ×2 [registered; fact:lines]: “User is on a single-line phone plan.” ← “it’s just me on the plan”
- memory m049 ×1 [unknown; -]: “User wants to compare mobile phone plans to find a cheaper or better one.” ← “I want to compare mobile phone plans and pick a cheaper or better one.”
- memory m012 ×4 [registered; person:partner]: “User's husband is joining the trip.” ← “my husband is coming with me”
- memory m002 ×2 [registered; fact:monthly_bill_usd]: “User's current phone bill is around $75 per month.” ← “my bill is around $75”
- memory m051 ×1 [registered; person:partner, person:self]: “User wants to reserve a table for two on Wednesday, the 9th of September, for dinner.” ← “Reserve a table for two on Wednesday, the 9th of September. It’s for dinner.”

## u009

**u009 S09 concert_ticket_booking** — slots: what you want: change the seats or date of a concert booking | the venue of the show you hold seats for: Harbor Street Thea | the day: Sunday, 11 January (say the weekday and the day num | the day: Sunday, 25 January (say the weekday and the day num | who is coming besides you: your wife, your son, your daughte | how many tickets: 4
- User: I want to change the seats or date of our 4-ticket concert booking. We're going with my wife, my son, and my daughter on Sunday, the 11th of January, or maybe Sunday, the 25th of January.
- Assistant: Got it. Do you have a place in mind?
- User: We have the tickets for the Harbor Street Theater show. Can you check the 11th or 25th of January for seat changes or a different date?
- Assistant: Here is what I'll look for: at Harbor Street Theater; Sunday, the 11th; Sunday, the 25th; with your wife, your son, your daughter; for 4 tickets.
**u009 S11 restaurant_reservation** — slots: what you want: find a place for a weekend lunch and reserve  | the day: Saturday, 24 January (say the weekday and the day n | the time: about 11:30 am | how many people: 1
- User: Find a place for a weekend lunch and reserve it. This Saturday, the 24th.
- Assistant: Sure. What time works for you?
- User: 11:30 am works for me. Just one person.
- Assistant: Here is what I'll look for: Saturday, the 24th; around 11:30 am; for 1 person.
- memory m038 ×1 [registered; fact:grocery_service]: “User requested a grocery delivery for Thursday, the 16th, with PantryRun.” ← “Set up this week's grocery delivery with PantryRun for this Thursday, the 16th.”
- memory m021 ×1 [registered; catalog:restaurants:r5]: “User's current reservation is at Alder & Rye.” ← “It's at Alder & Rye.”
- memory m019 ×1 [unknown; -]: “User wants to move an existing dinner reservation to a different time.” ← “I want to move an existing dinner reservation to a different time.”
- memory m030 ×1 [registered; catalog:concerts:c3]: “User has tickets for the Harbor Street Theater show.” ← “We have the tickets for the Harbor Street Theater show.”
- memory m045 ×1 [registered; -]: “User plans to drive to Elk Meadow.” ← “I’ll drive there”

## u010

**u010 S01 weekend_trip_booking** — slots: what you want: pick a destination for a short getaway and ch | the day: Friday, 31 October (say the weekday and the day num | the day: Sunday, 2 November (say the weekday and the day num | how you would travel: by car | who is coming besides you: your friend | how many travellers: 2
- User: I want to plan a short getaway from Friday, the 31st of October, to Sunday, the 2nd of November, by car, for two people. Let’s pick a destination and check transport options.
- Assistant: Got it. Who will be coming with you?
- User: My friend is coming with me. Let’s plan the trip from this Friday, the 31st of October, to Sunday, the 2nd of November.
- Assistant: Here is what I'll look for: Friday, the 31st; Sunday, the 2nd; by car; with your friend; for 2 travellers.
**u010 S04 fitness_class_booking** — slots: what you want: find a class time that fits your week and boo | the class you want to try: indoor climbing | the day: Thursday, 27 November (say the weekday and the day  | the day: Sunday, 30 November (say the weekday and the day nu | a time preference: you prefer afternoon events and being hom
- User: Hey, I want to find a time for an indoor climbing trial class that fits my week. I'm free on Thursday, the 27th of November, and Sunday, the 30th of November. I prefer afternoon sessions and being home by 9 pm.
- Assistant: Here is what I'll look for: a indoor climbing class; Thursday, the 27th; Sunday, the 30th; preferring afternoon events and being home by 9 pm.
- memory m029 ×1 [registered; catalog:weekend_destinations:d2]: “User wants to go on a short getaway to Cedar Ridge from August 21st to 23rd.” ← “I want to pick a destination for a short getaway and check transport options. I'm thinking of going to Cedar Ridge from Friday, the 21st of August to Sunday, the 23rd of August.”
- memory m033 ×1 [registered; -]: “User is looking for concerts in town on Friday, the 9th of October.” ← “I'm looking for upcoming concerts in town that would suit me and have seats available. Any suggestions for Friday, the 9th of October?”
- memory m004 ×1 [unknown; -]: “User wants to compare mobile phone plans to find a cheaper or better one.” ← “I want to compare mobile phone plans and pick a cheaper or better one.”
- memory m001 ×1 [registered; -]: “User wants to plan a short getaway from Friday, 31st October, to Sunday, 2nd November, by car.” ← “I want to plan a short getaway from Friday, the 31st of October, to Sunday, the 2nd of November, by car”
- memory m002 ×1 [registered; person:friend]: “User is traveling with a friend.” ← “My friend is coming with me”

## u011

**u011 S06 fitness_class_booking** — slots: what you want: find a class time that fits your week and boo | the class you want to try: pilates | the day: Wednesday, 24 June (say the weekday and the day num | the day: Saturday, 27 June (say the weekday and the day numb
- User: I want to find a pilates class time that fits my week and book a trial session. Let me know what's available on this Wednesday, the 24th, and Saturday, the 27th of June.
- Assistant: Here is what I'll look for: a pilates class; Wednesday, the 24th; Saturday, the 27th.
**u011 S09 fitness_class_booking** — slots: what you want: sign up for a fitness class or a class pack a | the class you want to try: spin | the gym: Riverbend Yoga | the day: Wednesday, 22 July (say the weekday and the day num | the day: Thursday, 23 July (say the weekday and the day numb | a time preference: you prefer evening events | who is coming besides you: your friend
- User: I want to sign up for a fitness class or a class pack at a local gym. I’m available this Wednesday, the 22nd, and Thursday, the 23rd of July.
- Assistant: Thanks. Do you have a place in mind?
- User: I want to sign up at Riverbend Yoga. My friend is coming too. We’re available this Wednesday, the 22nd, and Thursday, the 23rd.
- Assistant: Got it. Which class would you like to try?
- User: Let’s try spin. I prefer evening classes.
- Assistant: Here is what I'll look for: a spin class; at Riverbend Yoga; Wednesday, the 22nd; Thursday, the 23rd; preferring evening events; with your friend.
- memory m018 ×1 [registered; -]: “User requested a morning delivery slot for Thursday, the 12th.” ← “Morning slot on Thursday, the 12th.”
- memory m020 ×1 [registered; -]: “User is interested in pilates class availability on Wednesday, the 24th, and Saturday, the 27th of June.” ← “Let me know what's available on this Wednesday, the 24th, and Saturday, the 27th of June.”
- memory m033 ×1 [registered; person:self, pref:seating]: “User wants one ticket and prefers aisle seating.” ← “One ticket, and I’d prefer aisle seating.”
- memory m034 ×1 [registered; fact:monthly_use_gb]: “User uses about 3 GB of data per month.” ← “I use about 3 GB of data a month”
- memory m014 ×2 [registered; -]: “User will be driving to Cedar Ridge.” ← “and would drive there”

## u012

**u012 S10 concert_ticket_booking** — slots: what you want: change the seats or date of a concert booking | the venue of the show you hold seats for: Harbor Street Thea | the day: Saturday, 20 June (say the weekday and the day numb | the day: Sunday, 5 July (say the weekday and the day number, | who is coming besides you: your friend | how many tickets: 2
- User: I want to change the seats or the date of my concert booking at Harbor Street Theater. The original date is Saturday, the 20th of June, but I'm considering moving to Sunday, the 5th of July. My friend is coming with me.
- Assistant: Got it. How many tickets is it for?
- User: It’s for two tickets.
- Assistant: Here is what I'll look for: at Harbor Street Theater; Saturday, the 20th; Sunday, the 5th; with your friend; for 2 tickets.
**u012 S04 restaurant_reservation** — slots: what you want: find a place for a weekend lunch and reserve  | who is coming besides you: your husband | the day: Sunday, 1 March (say the weekday and the day number | the time: about 1:00 pm | how many people: 2
- User: Find a place for a weekend lunch and reserve it. I want it on this Sunday, the 1st, around 1:00 pm.
- Assistant: Okay. How many people is it for?
- User: It's just my husband and me, so two people total.
- Assistant: Here is what I'll look for: with your husband; Sunday, the 1st; around 1:00 pm; for 2 people.
- memory m023 ×1 [registered; -]: “User listed tomatoes, lentils, spinach, and apples as the items to be added to the order.” ← “Tomatoes, lentils, spinach, and apples.”
- memory m011 ×1 [quote_mismatch; -]: “User wants the vacation rental to have a kitchen.” ← “One with a kitchen so I can cook.”
- memory m032 ×1 [registered; pref:schedule]: “User prefers evening events.” ← “and I prefer evening events.”
- memory m024 ×2 [registered; -]: “User wants to sign up for a pilates class at Summit Climb & Train.” ← “Let me try pilates. Sign me up for the class this Friday, the 5th.”
- memory m018 ×2 [registered; person:partner, person:self]: “User is going to the lunch with two people total.” ← “so two people total.”

## u013

**u013 S02 concert_ticket_booking** — slots: what you want: change the seats or date of a concert booking | the venue of the show you hold seats for: Harbor Street Thea | the day: Saturday, 20 December (say the weekday and the day  | what you want changed: seats closer to the aisle | who is coming besides you: your mother, your father | how many tickets: 3
- User: I want to change the seats or date of a concert booking. It's this Saturday, the 20th.
- Assistant: Sure. Do you have a place in mind?
- User: I want to change to seats closer to the aisle for the concert at Harbor Street Theater.
- Assistant: Sure. Who will be coming with you?
- User: It’s for three of us—my mom, my dad, and me.
- Assistant: Here is what I'll look for: at Harbor Street Theater; Saturday, the 20th; seats closer to the aisle; with your mother, your father; for 3 tickets.
**u013 S12 restaurant_reservation** — slots: what you want: reserve a table for a dinner out | who is coming besides you: your friend | the day: Monday, 14 September (say the weekday and the day n | the time: about 6:30 pm | the restaurant you have in mind: Juniper Table | your diet: vegetarian | how many people: 2
- User: Reserve a table for two for Monday, the 14th. It’s for dinner out.
- Assistant: Thanks. What time works for you?
- User: How about 6:30 pm on Monday, the 14th? We want to go to Juniper Table.
- Assistant: Got it. Who will be coming with you?
- User: It's just me and my friend. I'm vegetarian.
- Assistant: Here is what I'll look for: with your friend; Monday, the 14th; around 6:30 pm; at Juniper Table; vegetarian options; for 2 people.
- memory m028 ×1 [registered; -]: “User wants to try a strength training class.” ← “Let’s try strength training.”
- memory m010 ×2 [registered; fact:grocery_service]: “User wants to use FreshCart for grocery delivery.” ← “I want to use FreshCart”
- memory m034 ×1 [registered; -]: “User wants to travel to Cedar Ridge by train or bus.” ← “I’d like to travel by train or bus.”
- memory m029 ×1 [registered; person:friend]: “User is planning a weekend lunch with a friend on Sunday, the 26th of July, around 12:30 pm.” ← “Find a place for a weekend lunch with my friend and reserve it. We're going on Sunday, the 26th of July, around 12:30 pm.”
- memory m023 ×1 [registered; -]: “User requested a grocery delivery for Sunday, the 22nd, in the afternoon.” ← “Set up this week's grocery delivery for this Sunday, the 22nd, in the afternoon.”

## u014

**u014 S11 weekend_trip_booking** — slots: what you want: pick a destination for a short getaway and ch | the day: Friday, 12 June (say the weekday and the day number | the day: Sunday, 14 June (say the weekday and the day number | how you would travel: by train or bus | who is coming besides you: your wife | how many travellers: 2
- User: Pick a destination for a short getaway and check transport options. I want to leave on Friday, the 12th of June, and return on Sunday, the 14th of June.
- Assistant: Sure. Who will be coming with you?
- User: My wife is coming with me. That’s two of us total.
- Assistant: Thanks. How would you like to travel?
- User: Let’s travel by train. We want to leave on Friday, the 12th, and come back on Sunday, the 14th.
- Assistant: Here is what I'll look for: Friday, the 12th; Sunday, the 14th; by train or bus; with your wife; for 2 travellers.
**u014 S05 restaurant_reservation** — slots: what you want: reserve a table for a dinner out | the day: Monday, 5 January (say the weekday and the day numb | the time: about 7:30 pm | the restaurant you have in mind: Blue Kettle Kitchen | how many people: 1
- User: Reserve a table for a dinner out at Blue Kettle Kitchen on this Monday, the 5th, around 7:30 pm.
- Assistant: Okay. How many people is it for?
- User: One person.
- Assistant: Here is what I'll look for: Monday, the 5th; around 7:30 pm; at Blue Kettle Kitchen; for 1 person.
- memory m029 ×1 [registered; -]: “User wants to go on a short getaway from Friday, the 12th of June, to Sunday, the 14th of June.” ← “Pick a destination for a short getaway and check transport options. I want to leave on Friday, the 12th of June, and return on Sunday, the 14th of June.”
- memory m027 ×2 [registered; fact:lines, person:partner]: “User's phone plan has 2 lines — one for the user and one for their wife.” ← “there are 2 lines on the plan — mine and my wife’s”
- memory m013 ×3 [registered; fact:monthly_use_gb]: “User uses about 3 GB of data per month.” ← “I use about 3 GB a month”
- memory m011 ×1 [unknown; -]: “User is considering changing their phone plan to pay less.” ← “Hey, I want to check whether I should change my current phone plan. Can you help me with that?”
- memory m012 ×2 [registered; fact:plan_data]: “User's current phone plan includes 15 GB of data for the whole plan.” ← “My current plan has 15 GB total for the whole plan”

## u015

**u015 S04 weekend_trip_booking** — slots: what you want: plan a two-night weekend trip and look up pla | the day: Friday, 6 February (say the weekday and the day num | the day: Sunday, 8 February (say the weekday and the day num | how you would travel: by train or bus | the kind of place to stay: cabin | something you would like to do there: rock climbing | how many travellers: 1
- User: Plan a two-night weekend trip for me from Friday, the 6th of February to Sunday, the 8th. I’ll travel by train or bus and am traveling alone.
- Assistant: Thanks. Anything you'd like to do there?
- User: I want to stay in a cabin and try rock climbing.
- Assistant: Here is what I'll look for: Friday, the 6th; Sunday, the 8th; by train or bus; a cabin; rock climbing; for 1 traveller.
**u015 S11 grocery_delivery** — slots: what you want: reorder the usual groceries and choose a deli | the grocery service you use: FreshCart | the day: Tuesday, 22 September (say the weekday and the day  | the delivery slot: evening | your usual items: spinach, olive oil, carrots, rice, potatoe
- User: Hey, I want to reorder my usual groceries through FreshCart and pick a delivery slot. Let me do this Tuesday, the 22nd.
- Assistant: Sure. Which delivery slot suits you?
- User: Evening slot on Tuesday, the 22nd. Reorder the usual: spinach, olive oil, carrots, rice, potatoes.
- Assistant: Here is what I'll look for: through FreshCart; Tuesday, the 22nd; evening delivery; spinach, olive oil, carrots, rice, potatoes.
- memory m037 ×1 [registered; fact:usual_items]: “User's usual grocery items include spinach, olive oil, carrots, rice, and potatoes.” ← “Reorder the usual: spinach, olive oil, carrots, rice, potatoes.”
- memory m010 ×3 [registered; person:friend]: “User will be dining with one friend.” ← “Just me and a friend.”
- memory m016 ×2 [registered; pref:hobbies]: “User wants to try rock climbing during the trip.” ← “and try rock climbing”
- memory m029 ×1 [registered; -]: “User wants to book a yoga class trial session.” ← “I want to find a yoga class time that fits my week and book a trial session.”
- memory m005 ×3 [registered; fact:lines]: “User is on a single line.” ← “I’m on a single line”

## u016

**u016 S11 restaurant_reservation** — slots: what you want: find a place for a weekend lunch and reserve  | the day: Sunday, 15 February (say the weekday and the day nu | the time: about 11:30 am | how many people: 1
- User: Find a place for a weekend lunch and reserve it. I want it on Sunday, the 15th, around 11:30 am.
- Assistant: Thanks. How many people is it for?
- User: For one person.
- Assistant: Here is what I'll look for: Sunday, the 15th; around 11:30 am; for 1 person.
**u016 S14 fitness_class_booking** — slots: what you want: find a class time that fits your week and boo | the class you want to try: pilates | the day: Wednesday, 22 April (say the weekday and the day nu | the day: Saturday, 25 April (say the weekday and the day num | a time preference: you prefer evening events
- User: Hey, I want to find a pilates class that fits my week and book a trial session. I'm free this Wednesday, the 22nd, and Saturday, the 25th of April, and I prefer evening events.
- Assistant: Here is what I'll look for: a pilates class; Wednesday, the 22nd; Saturday, the 25th; preferring evening events.
- memory m027 ×1 [unknown; -]: “User is considering changing their current phone plan.” ← “I want to check whether to change my current phone plan.”
- memory m044 ×1 [registered; -]: “User is available for the trial session on Monday, the 10th of August, or Wednesday, the 12th of August.” ← “Let me know if there are any available on Monday, the 10th of August, or Wednesday, the 12th of August.”
- memory m040 ×1 [registered; fact:grocery_service]: “User requested an afternoon delivery slot with DailyCrate on Saturday, the 6th.” ← “Afternoon slot with DailyCrate this Saturday, the 6th.”
- memory m002 ×2 [registered; fact:grocery_service]: “User uses the grocery service called DailyCrate.” ← “I use DailyCrate.”
- memory m034 ×1 [registered; -]: “User wants to pay less for their phone plan.” ← “I want to pay less”

## u017

**u017 S09 fitness_class_booking** — slots: what you want: find a class time that fits your week and boo | the class you want to try: spin | the day: Tuesday, 31 March (say the weekday and the day numb | the day: Friday, 3 April (say the weekday and the day number | a time preference: you prefer afternoon events and being hom | who is coming besides you: your friend
- User: Hey, I want to find a class time that fits my week and book a trial session. Let me know what's available on Tuesday, the 31st of March, and Friday, the 3rd of April.
- Assistant: Okay. Who will be coming with you?
- User: I want to try a spin class with my friend. Let me know what times are available on Tuesday, the 31st, and Friday, the 3rd.
- Assistant: Sure. What time of day suits you best?
- User: Afternoon works best for me—I prefer to be home by 9 pm.
- Assistant: Here is what I'll look for: a spin class; Tuesday, the 31st; Friday, the 3rd; preferring afternoon events and being home by 9 pm; with your friend.
**u017 S08 mobile_plan_purchase** — slots: what you want: compare mobile phone plans and pick a cheaper | your current carrier: Beacon Wireless | your current plan's data: unlimited in total for the whole p | how much data you use: about 22 GB a month | your monthly bill: about $145 | how many lines on the plan: 4 (you and your mother, your fat | why: you want to pay less
- User: I want to compare mobile phone plans and pick a cheaper or better one.
- Assistant: Okay. How much data do you use in a month?
- User: My current plan has unlimited data for the whole plan, but I use about 22 GB a month. I’m paying around $145 every month.
- Assistant: Thanks. How many lines on the plan is it for?
- User: My current carrier is Beacon Wireless, and the plan has 4 lines — me, my mom, dad, and brother. I want to pay less.
- Assistant: Here is what I'll look for: currently with Beacon Wireless; current plan unlimited; about 22 GB used a month; about $145 a month now; for 4 lines; you want to pay less.
- memory m037 ×1 [registered; fact:carrier]: “User is with Beacon Wireless.” ← “Beacon Wireless.”
- memory m023 ×1 [unknown; -]: “User is looking to compare and switch to a cheaper or better mobile phone plan.” ← “I want to compare mobile phone plans and pick a cheaper or better one.”
- memory m034 ×2 [registered; fact:monthly_use_gb]: “User uses about 22 GB of data per month.” ← “I use about 22 GB of data a month”
- memory m041 ×1 [registered; catalog:restaurants:r4, person:friend, person:self]: “User's reservation is for two people — themselves and their friend — at Alder & Rye.” ← “It's for two people — me and my friend — at Alder & Rye.”
- memory m006 ×1 [registered; pref:seating]: “User wants aisle seats for the live music show.” ← “I want aisle seats for four people”

## u018

**u018 S09 concert_ticket_booking** — slots: what you want: ask which upcoming concerts in town would sui | the day: Sunday, 1 March (say the weekday and the day number | a time preference: you prefer morning activities | who is coming besides you: your wife, your 8-year-old son, y | how many tickets: 4
- User: This Sunday, the 1st, I want to know which upcoming concerts in town would suit you and hold seats for 4 people.
- Assistant: Got it. What time of day suits you best?
- User: Morning is better for me. Coming are my wife, my eight-year-old son, and my seven-year-old son.
- Assistant: Here is what I'll look for: Sunday, the 1st; preferring morning activities; with your wife, your 8-year-old son, your 7-year-old son; for 4 tickets.
**u018 S03 restaurant_reservation** — slots: what you want: move an existing dinner reservation to a diff | who is coming besides you: your wife | the restaurant where you have a reservation: Marigold Diner | the day: Friday, 21 November (say the weekday and the day nu | the time of the reservation now: about 6:00 pm | the new time you want: about 6:30 pm | how many people: 2
- User: I want to move my dinner reservation at Marigold Diner to this Friday, the 21st.
- Assistant: Thanks. What time works for you?
- User: It’s currently set for about 6:00 pm. I’d like to move it to 6:30 pm this Friday, the 21st.
- Assistant: Got it. Who will be coming with you?
- User: Just me and my wife. That's two people total.
- Assistant: Here is what I'll look for: with your wife; at Marigold Diner; Friday, the 21st; around 6:00 pm; around 6:30 pm; for 2 people.
- memory m023 ×1 [registered; -]: “User's mobile bill recently went up, prompting them to look for a cheaper option.” ← “The bill went up recently, so I want to see if we can switch to something cheaper.”
- memory m016 ×1 [registered; -]: “User is free on Tuesday, the 10th of February, and Thursday, the 12th of February.” ← “I'm free on Tuesday, the 10th of February, and Thursday, the 12th of February.”
- memory m025 ×1 [registered; -]: “User specified the afternoon slot for delivery on Wednesday the 25th.” ← “Afternoon slot on Wednesday the 25th, please.”
- memory m001 ×1 [registered; -]: “User wants to reorder their usual groceries and pick a delivery slot for Thursday, the 9th.” ← “Reorder the usual groceries and pick a delivery slot for this Thursday, the 9th.”
- memory m018 ×2 [unknown; -]: “User is looking to compare mobile phone plans to find a cheaper or better one.” ← “I need you to compare mobile phone plans and help me pick a cheaper or better one.”

## u019

**u019 S06 grocery_delivery** — slots: what you want: set up this week's grocery delivery | the grocery service you use: DailyCrate | the day: Sunday, 25 January (say the weekday and the day num | the delivery slot: afternoon | your diet: gluten-free
- User: Let's set up this week's grocery delivery for Sunday, the 25th.
- Assistant: Sure. Which grocery service do you use?
- User: I use DailyCrate. Let's schedule the delivery for the afternoon on Sunday, the 25th.
- Assistant: Thanks. Any dietary needs I should keep in mind?
- User: I'm on a gluten-free diet. Can you make sure the options are gluten-free?
- Assistant: Here is what I'll look for: through DailyCrate; Sunday, the 25th; afternoon delivery; gluten-free options.
**u019 S19 fitness_class_booking** — slots: what you want: find a class time that fits your week and boo | the class you want to try: yoga | the day: Thursday, 1 October (say the weekday and the day nu | the day: Sunday, 4 October (say the weekday and the day numb | who is coming besides you: your husband
- User: Hi, I want to find a class time that fits my week and book a trial session. I'm free on Thursday, the 1st of October, and Sunday, the 4th of October. My husband is coming with me.
- Assistant: Got it. Which class would you like to try?
- User: I want to try the yoga class. Can you check Thursday, the 1st, or Sunday, the 4th for a trial session?
- Assistant: Here is what I'll look for: a yoga class; Thursday, the 1st; Sunday, the 4th; with your husband.
- memory m027 ×1 [registered; -]: “User prefers the evening delivery slot on the 20th.” ← “This Friday, the 20th, I want the evening slot with my usual items”
- memory m023 ×1 [registered; -]: “User prefers afternoon delivery for the grocery order.” ← “Afternoon slot.”
- memory m042 ×1 [registered; catalog:weekend_destinations:d2]: “User is planning to go to Elk Meadow.” ← “I'm thinking of going to Elk Meadow.”
- memory m034 ×1 [quote_mismatch; -]: “User prefers concerts with seating rather than standing.” ← “Can you find ones that have 2 tickets available?”
- memory m026 ×2 [registered; fact:household_size]: “User's order is for 4 people.” ← “The order is for 4 people”

## u020

**u020 S04 weekend_trip_booking** — slots: what you want: plan a two-night weekend trip and look up pla | the day: Friday, 23 January (say the weekday and the day num | the day: Sunday, 25 January (say the weekday and the day num | how you would travel: by train or bus | the kind of place to stay: hotel | something you would like to do there: hiking | how many travellers: 1
- User: Plan a two-night weekend trip for Friday, the 23rd of January, through Sunday, the 25th of January. I need help finding places to stay.
- Assistant: Got it. How many travellers is it for?
- User: I’ll travel by train. Just me. Looking for places to stay Friday the 23rd through Sunday the 25th.
- Assistant: Thanks. Anything you'd like to do there?
- User: I want to stay in a hotel and do some hiking while I'm there.
- Assistant: Here is what I'll look for: Friday, the 23rd; Sunday, the 25th; by train or bus; a hotel; hiking; for 1 traveller.
**u020 S10 fitness_class_booking** — slots: what you want: find a class time that fits your week and boo | the class you want to try: indoor climbing | the day: Tuesday, 7 July (say the weekday and the day number | the day: Sunday, 12 July (say the weekday and the day number | a time preference: you prefer evening events | who is coming besides you: your friend
- User: Hi, I want to find a class time that fits my week and book a trial session. Please check availability for this Tuesday, the 7th, and Sunday, the 12th of July.
- Assistant: Okay. Which class would you like to try?
- User: I want to try the indoor climbing class. My friend is coming with me.
- Assistant: Got it. What time of day suits you best?
- User: I prefer evening classes. Let me know what times are available for Tuesday the 7th and Sunday the 12th.
- Assistant: Here is what I'll look for: a indoor climbing class; Tuesday, the 7th; Sunday, the 12th; preferring evening events; with your friend.
- memory m018 ×1 [registered; person:friend, person:self]: “User is booking two tickets for the event.” ← “Let’s book two tickets for this Friday, the 23rd.”
- memory m004 ×2 [registered; fact:carrier]: “User is with Clearwave for their phone plan.” ← “I’m with Clearwave”
- memory m024 ×1 [unknown; -]: “User is looking to compare mobile phone plans to find a cheaper or better one.” ← “Can you help me compare mobile phone plans and find a cheaper or better one?”
- memory m028 ×1 [registered; -]: “User wants to book a trial session for an indoor climbing class.” ← “I want to try the indoor climbing class”
- memory m015 ×1 [registered; pref:hobbies]: “User wants to do some hiking during the trip.” ← “do some hiking while I'm there”

## u021

**u021 S02 mobile_plan_purchase** — slots: what you want: check whether to change your current phone pl | your current carrier: Clearwave | your current plan's data: 10 GB | how much data you use: about 22 GB a month | your monthly bill: about $75 | how many lines on the plan: 1 | why: you want to pay less
- User: I want to check whether to change my current phone plan with Clearwave. Let me know what I should look into.
- Assistant: Got it. How many lines on the plan is it for?
- User: I use about 22 GB of data a month, my bill is around $75, and it's just one line.
- Assistant: Okay. How much data does your current plan have?
- User: My current plan has 10 GB of data. I want to pay less.
- Assistant: Here is what I'll look for: currently with Clearwave; current plan 10 GB; about 22 GB used a month; about $75 a month now; for 1 line; you want to pay less.
**u021 S15 grocery_delivery** — slots: what you want: set up this week's grocery delivery | the grocery service you use: DailyCrate | the day: Wednesday, 30 September (say the weekday and the da | the delivery slot: afternoon | your diet: gluten-free
- User: Set up this week's grocery delivery for this Wednesday, the 30th.
- Assistant: Thanks. Which delivery slot suits you?
- User: Afternoon slot with DailyCrate on Wednesday, the 30th.
- Assistant: Got it. Any dietary needs I should keep in mind?
- User: I'm on a gluten-free diet.
- Assistant: Here is what I'll look for: through DailyCrate; Wednesday, the 30th; afternoon delivery; gluten-free options.
- memory m031 ×1 [registered; -]: “User is interested in concert dates on Saturday, the 30th of May or Sunday, the 7th of June.” ← “Check options for Saturday, the 30th of May or Sunday, the 7th of June.”
- memory m029 ×1 [registered; -]: “User is available on Tuesday, the 19th of May, and Sunday, the 24th of May.” ← “My free days are Tuesday, the 19th of May, and Sunday, the 24th of May.”
- memory m035 ×1 [registered; pref:seating]: “User prefers aisle seats at concerts.” ← “I prefer aisle seats.”
- memory m022 ×1 [registered; person:friend]: “User will be driving to the destination and is bringing a friend.” ← “We’ll drive there ourselves, and my friend is coming with me.”
- memory m021 ×1 [registered; -]: “User is planning a two-night weekend trip for Friday, 27th February, and Sunday, 1st March.” ← “Plan a two-night weekend trip for Friday, the 27th of February, and Sunday, the 1st of March.”

## u022

**u022 S01 restaurant_reservation** — slots: what you want: move an existing dinner reservation to a diff | the restaurant where you have a reservation: Alder & Rye | the day: Thursday, 16 October (say the weekday and the day n | the time of the reservation now: about 8:30 pm | the new time you want: about 7:30 pm | how many people: 1
- User: I want to move my dinner reservation at Alder & Rye to this Thursday, the 16th.
- Assistant: Sure. What time works for you?
- User: The reservation is currently for about 8:30 pm this Thursday, the 16th. I’d like to change it to about 7:30 pm instead.
- Assistant: Got it. How many people is it for?
- User: It’s for one person. Let me know if that works.
- Assistant: Here is what I'll look for: at Alder & Rye; Thursday, the 16th; around 8:30 pm; around 7:30 pm; for 1 person.
**u022 S05 concert_ticket_booking** — slots: what you want: change the seats or date of a concert booking | the venue of the show you hold seats for: Granite Arts Cente | the day: Sunday, 14 December (say the weekday and the day nu | what you want changed: seats closer to the aisle | how many tickets: 1
- User: I want to change the seats or the date of my concert booking at Granite Arts Center. The current ticket is for Sunday, the 14th of December, and I have one ticket.
- Assistant: Okay. What would you like to change?
- User: I want to change my seats to ones closer to the aisle for the Sunday, the 14th of December concert.
- Assistant: Here is what I'll look for: at Granite Arts Center; Sunday, the 14th; seats closer to the aisle; for 1 ticket.
- memory m029 ×1 [registered; -]: “User prefers a morning delivery slot.” ← “Morning slot works best for me.”
- memory m036 ×1 [unknown; -]: “User is traveling with one other person (a friend).” ← “Just the two of us”
- memory m001 ×1 [registered; -]: “User wants to change their dinner reservation at Alder & Rye from 8:30 pm to 7:30 pm on Thursday, the 16th.” ← “The reservation is currently for about 8:30 pm this Thursday, the 16th. I’d like to change it to about 7:30 pm instead.”
- memory m030 ×1 [unknown; -]: “User wants to sign up for a swimming class or class pack at a local gym.” ← “I want to sign up for a fitness class or a class pack at a local gym.”
- memory m033 ×1 [registered; -]: “User wants to plan a two-night weekend trip to Elk Meadow starting on Friday, the 31st of July, and ending on Sunday, the 2nd of August.” ← “Plan a two-night weekend trip for Friday, the 31st of July, and Sunday, the 2nd of August.”

## u023

**u023 S09 concert_ticket_booking** — slots: what you want: ask which upcoming concerts in town would sui | the day: Friday, 3 July (say the weekday and the day number, | a time preference: you enjoy late-night events | who is coming besides you: your friend | how many tickets: 2
- User: Hey, I'm looking for upcoming concerts in town that would be good for Friday, the 3rd of July. Can you find ones that still have seats for 2 tickets?
- Assistant: Sure. What time of day suits you best?
- User: I like late-night events, and my friend is coming with me.
- Assistant: Here is what I'll look for: Friday, the 3rd; enjoying late-night events; with your friend; for 2 tickets.
**u023 S08 mobile_plan_purchase** — slots: what you want: check whether to change your current phone pl | your current carrier: Juno Cellular | your current plan's data: unlimited | how much data you use: about 3 GB a month | your monthly bill: about $75 | how many lines on the plan: 1 | why: calls drop at home sometimes
- User: I want to check if I should change my phone plan because sometimes calls drop at home.
- Assistant: Thanks. How much data does your current plan have?
- User: My plan is unlimited data, and I use about 3 GB a month. It’s just one line.
- Assistant: Thanks. Which carrier are you with now?
- User: I'm with Juno Cellular, and my bill is about $75 a month.
- Assistant: Here is what I'll look for: currently with Juno Cellular; current plan unlimited; about 3 GB used a month; about $75 a month now; for 1 line; calls drop at home sometimes.
- memory m016 ×1 [registered; -]: “User is interested in yoga classes on Friday, the 3rd, and Sunday, the 5th.” ← “Let me know about sessions on this Friday, the 3rd, and this Sunday, the 5th.”
- memory m021 ×1 [registered; fact:carrier]: “User is currently with Juno Cellular.” ← “I'm with Juno Cellular”
- memory m033 ×1 [registered; -]: “User wants to attend a live music show on Saturday, the 19th.” ← “I want you to find and book tickets for a live music show this Saturday, the 19th.”
- memory m027 ×1 [registered; -]: “User prefers the lunch reservation to be around 1:00 pm on Saturday, the 27th.” ← “How about about 1:00 pm this Saturday, the 27th?”
- memory m013 ×1 [registered; fact:grocery_service]: “User prefers the afternoon delivery slot with FreshCart for this order.” ← “Afternoon slot with FreshCart this Friday, the 27th.”

## u024

**u024 S02 concert_ticket_booking** — slots: what you want: find and book tickets for a live music show o | the day: Saturday, 1 November (say the weekday and the day n | the kind of music: R&B or classic rock | seating: you prefer seated venues over standing | who is coming besides you: your wife | how many tickets: 2
- User: Find and book tickets for a live music show this Saturday, the 1st of November. My wife is coming with me.
- Assistant: Thanks. Any seating preference?
- User: I want R&B or classic rock. I prefer seated venues over standing.
- Assistant: Thanks. How many tickets is it for?
- User: Two tickets please.
- Assistant: Here is what I'll look for: Saturday, the 1st; R&B or classic rock; preferring seated venues over standing; with your wife; for 2 tickets.
**u024 S07 mobile_plan_purchase** — slots: what you want: check whether to change your current phone pl | your current carrier: Juno Cellular | your current plan's data: 5 GB | how much data you use: about 22 GB a month | your monthly bill: about $65 | how many lines on the plan: 1 | why: you want to pay less
- User: I want to check whether to change my current phone plan.
- Assistant: Sure. Which carrier are you with now?
- User: I'm with Juno Cellular, on a 5 GB plan, but I use about 22 GB a month.
- Assistant: Sure. How much do you pay each month now?
- User: I pay about $65 a month for the 5 GB plan, and there's just one line on it. I want to pay less.
- Assistant: Here is what I'll look for: currently with Juno Cellular; current plan 5 GB; about 22 GB used a month; about $65 a month now; for 1 line; you want to pay less.
- memory m045 ×1 [registered; -]: “User's phone bill recently increased.” ← “because it went up recently”
- memory m032 ×1 [registered; -]: “User is available for classes on Saturday, the 18th, and Tuesday, the 21st of April.” ← “I'm available this Saturday, the 18th, and Tuesday, the 21st of April.”
- memory m022 ×2 [registered; fact:monthly_bill_usd]: “User pays about $65 a month for their current plan.” ← “I pay about $65 a month for the 5 GB plan”
- memory m005 ×2 [registered; pref:music]: “User prefers R&B or classic rock music for the event.” ← “I want R&B or classic rock.”
- memory m048 ×1 [registered; fact:usual_items]: “User listed spinach, rice, black beans, bell peppers, and carrots as the groceries to reorder.” ← “Spinach, rice, black beans, bell peppers, carrots.”

## u025

**u025 S03 grocery_delivery** — slots: what you want: reorder the usual groceries and choose a deli | the grocery service you use: PantryRun | the day: Wednesday, 3 December (say the weekday and the day  | the delivery slot: afternoon | your usual items: black beans, onions, carrots, bananas, len | how many people the order is for (everyone at home): 2 | your diet: low-sodium
- User: Reorder the usual groceries and pick a delivery slot for this Wednesday, the 3rd, in the afternoon.
- Assistant: Okay. Which grocery service do you use?
- User: PantryRun. Low-sodium.
- Assistant: Thanks. Which items would you like?
- User: Black beans, onions, carrots, bananas, and lentils — that's the usual. It's for two people. Pick a Wednesday afternoon slot.
- Assistant: Here is what I'll look for: through PantryRun; Wednesday, the 3rd; afternoon delivery; black beans, onions, carrots, bananas, lentils; for 2 people; low-sodium options.
**u025 S05 fitness_class_booking** — slots: what you want: sign up for a fitness class or a class pack a | the class you want to try: spin | the gym: Corner Street Pilates | the day: Saturday, 20 December (say the weekday and the day  | the day: Wednesday, 24 December (say the weekday and the day | a time preference: you prefer evening events | who is coming besides you: your wife
- User: I want to sign up for a fitness class or a class pack at a local gym. I’d like to do it this Saturday, the 20th, or Wednesday, the 24th of December. I prefer evening events.
- Assistant: Got it. Do you have a place in mind?
- User: Corner Street Pilates, this Saturday, the 20th. My wife is coming too.
- Assistant: Thanks. Which class would you like to try?
- User: Let’s do the spin class this Saturday, the 20th. My wife is coming too.
- Assistant: Here is what I'll look for: a spin class; at Corner Street Pilates; Saturday, the 20th; Wednesday, the 24th; preferring evening events; with your wife.
- memory m038 ×1 [registered; fact:grocery_service]: “User uses PantryRun for grocery delivery.” ← “I use PantryRun.”
- memory m017 ×1 [registered; -]: “User is available to attend on Saturday, the 20th, or Wednesday, the 24th of December.” ← “I’d like to do it this Saturday, the 20th, or Wednesday, the 24th of December.”
- memory m021 ×1 [registered; catalog:gyms:g1]: “User wants to sign up for a strength training class at Riverbend Yoga.” ← “Let’s do strength training at Riverbend Yoga”
- memory m016 ×1 [unknown; -]: “User wants to sign up for a fitness class or class pack at a local gym.” ← “I want to sign up for a fitness class or a class pack at a local gym.”
- memory m007 ×1 [registered; -]: “User is requesting seats closer to the aisle for the concert.” ← “Can I get seats closer to the aisle?”

## u026

**u026 S02 fitness_class_booking** — slots: what you want: sign up for a fitness class or a class pack a | the class you want to try: pilates | the gym: Ironworks Gym | the day: Wednesday, 10 December (say the weekday and the day | the day: Thursday, 11 December (say the weekday and the day  | a time preference: you prefer afternoon events and being hom
- User: I want to sign up for a fitness class or a class pack at Ironworks Gym. I prefer classes on this Wednesday, the 10th, or this Thursday, the 11th, in the afternoon and to be home by 9 pm.
- Assistant: Sure. Which class would you like to try?
- User: Let’s try pilates on Wednesday, the 10th.
- Assistant: Here is what I'll look for: a pilates class; at Ironworks Gym; Wednesday, the 10th; Thursday, the 11th; preferring afternoon events and being home by 9 pm.
**u026 S04 weekend_trip_booking** — slots: what you want: pick a destination for a short getaway and ch | the day: Friday, 3 July (say the weekday and the day number, | the day: Sunday, 5 July (say the weekday and the day number, | where you are thinking of going: Port Alder | how you would travel: by train or bus | something you would like to do there: reading | who is coming besides you: your wife | how many travellers: 2
- User: Hey, I want to pick a destination for a short getaway and check transport options. I’d like to leave on Friday, the 3rd of July, and return on Sunday, the 5th.
- Assistant: Thanks. How many travellers is it for?
- User: Just me and my wife—so two of us. We’d like somewhere quiet where we can read and relax.
- Assistant: Okay. Where are you thinking of going?
- User: We were thinking of going to Port Alder. We’d like to check train or bus options for getting there.
- Assistant: Here is what I'll look for: Friday, the 3rd; Sunday, the 5th; going to Port Alder; by train or bus; reading; with your wife; for 2 travellers.
- memory m011 ×2 [registered; pref:hobbies]: “User wants a quiet destination where they can read and relax.” ← “We’d like somewhere quiet where we can read and relax.”
- memory m032 ×1 [registered; fact:monthly_bill_usd]: “User's current monthly bill is around $65.” ← “my bill is now around $65”
- memory m002 ×1 [registered; -]: “User is ordering groceries for Friday, the 21st, with the afternoon delivery slot.” ← “It's for this Friday, the 21st, with the afternoon delivery slot.”
- memory m029 ×1 [registered; person:partner, person:self]: “User is booking two tickets for the event.” ← “Two tickets, for this Saturday, the 5th.”
- memory m020 ×1 [registered; -]: “User wants to book a ticket for a live music show on Friday, 7th of August.” ← “I want to find and book tickets for a live music show on Friday, the 7th of August.”

## u027

**u027 S14 mobile_plan_purchase** — slots: what you want: check whether to change your current phone pl | your current carrier: Beacon Wireless | your current plan's data: 15 GB | how much data you use: about 22 GB a month | your monthly bill: about $70 | how many lines on the plan: 1 | why: calls drop at home sometimes
- User: I want to check whether to change my current phone plan. I'm with Beacon Wireless and I use about 22 GB a month.
- Assistant: Thanks. How much data does your current plan have?
- User: My current plan has 15 GB. I'm thinking about switching because calls drop at home sometimes.
- Assistant: Got it. How much do you pay each month now?
- User: I pay about $70 a month, and it's just me on the plan—only 1 line.
- Assistant: Here is what I'll look for: currently with Beacon Wireless; current plan 15 GB; about 22 GB used a month; about $70 a month now; for 1 line; calls drop at home sometimes.
**u027 S09 grocery_delivery** — slots: what you want: add items to a grocery order for a meal they  | the grocery service you use: PantryRun | the day: Friday, 13 February (say the weekday and the day nu | the delivery slot: evening | items to add: onions, spinach, olive oil, lentils | your diet: vegetarian
- User: Add items to the grocery order for the meal I'm cooking on this Friday, the 13th.
- Assistant: Got it. Which items would you like?
- User: Add onions, spinach, olive oil, and lentils to my PantryRun order for this Friday, the 13th.
- Assistant: Sure. Which delivery slot suits you?
- User: Evening slot, please. I’m vegetarian.
- Assistant: Here is what I'll look for: through PantryRun; Friday, the 13th; evening delivery; onions, spinach, olive oil, lentils; vegetarian options.
- memory m020 ×1 [registered; fact:grocery_service]: “User is placing an order for PantryRun delivery on Tuesday, the 6th, in the afternoon.” ← “Add items to my PantryRun order for this Tuesday, the 6th, afternoon delivery.”
- memory m054 ×1 [registered; person:friend, person:self]: “User wants to book two tickets for a live music show on Sunday, the 30th of August.” ← “Find and book tickets for a live music show on Sunday, the 30th of August. Need two tickets.”
- memory m043 ×1 [registered; person:partner, person:self, pref:diet]: “User wants vegetarian food for two on Sunday, the 29th.” ← “I want vegetarian food for two on Sunday, the 29th.”
- memory m040 ×1 [registered; -]: “User requested grocery delivery for this week to be set for Friday, the 27th.” ← “Set up this week's grocery delivery for this Friday, the 27th.”
- memory m017 ×1 [registered; -]: “User wants to change the date of a concert booking from Friday, the 12th of December, to Saturday, the 20th of December.” ← “I want to change the seats or date of the concert booking I'm considering. I'm looking at Friday, the 12th of December, or Saturday, the 20th of December.”

## u028

**u028 S17 fitness_class_booking** — slots: what you want: sign up for a fitness class or a class pack a | the class you want to try: spin | the gym: Northside Fitness Studio | the day: Sunday, 23 August (say the weekday and the day numb | the day: Friday, 28 August (say the weekday and the day numb | a time preference: you prefer evening events
- User: I want to sign up for a fitness class or a class pack at a local gym. I need it for this Sunday, the 23rd, and this Friday, the 28th.
- Assistant: Thanks. Do you have a place in mind?
- User: Let’s go with Northside Fitness Studio. I prefer evening classes.
- Assistant: Thanks. Which class would you like to try?
- User: Let’s do spin for this Sunday, the 23rd, and this Friday, the 28th.
- Assistant: Here is what I'll look for: a spin class; at Northside Fitness Studio; Sunday, the 23rd; Friday, the 28th; preferring evening events.
**u028 S06 restaurant_reservation** — slots: what you want: find a place for a weekend lunch and reserve  | the day: Saturday, 6 December (say the weekday and the day n | the time: about 12:30 pm | how many people: 1
- User: Find a place for a weekend lunch and reserve it. I want to book for this Saturday, the 6th.
- Assistant: Okay. What time works for you?
- User: How about 12:30 pm? Just me.
- Assistant: Here is what I'll look for: Saturday, the 6th; around 12:30 pm; for 1 person.
- memory m046 ×1 [registered; pref:seating]: “User prefers seated venues for the concert, not standing.” ← “We prefer seated venues, not standing.”
- memory m026 ×1 [registered; -]: “User wants to plan a two-night weekend trip from Friday, 6th of March to Sunday, 8th of March.” ← “I want to plan a two-night weekend trip for Friday, the 6th of March through Sunday, the 8th of March.”
- memory m006 ×1 [registered; -]: “User wants to move a dinner reservation to Saturday, the 8th.” ← “I want to move a dinner reservation to this Saturday, the 8th. Can you help with that?”
- memory m017 ×1 [registered; catalog:gyms:g2]: “User wants to sign up for a yoga class at Corner Street Pilates on Friday, the 2nd, and Saturday, the 3rd.” ← “I want to sign up for a yoga class at Corner Street Pilates this Friday, the 2nd, and this Saturday, the 3rd.”
- memory m002 ×1 [registered; -]: “User's grocery order is scheduled for Friday, the 17th, with evening delivery.” ← “for this Friday, the 17th, with the evening delivery slot.”

## u029

**u029 S08 concert_ticket_booking** — slots: what you want: find and book tickets for a live music show o | the day: Saturday, 7 March (say the weekday and the day numb | the kind of music: pop-punk or folk | seating: you prefer seated venues over standing | a time preference: you prefer evening events | who is coming besides you: your husband | how many tickets: 2
- User: Hey, I want to find and book tickets for a live music show this Saturday, the 7th of March. I’m looking for pop-punk or folk, and I prefer seated venues.
- Assistant: Sure. Who will be coming with you?
- User: Just me and my husband. We need 2 tickets.
- Assistant: Thanks. What time of day suits you best?
- User: Evening events are best for us. Can you find something on this Saturday, the 7th?
- Assistant: Here is what I'll look for: Saturday, the 7th; pop-punk or folk; preferring seated venues over standing; preferring evening events; with your husband; for 2 tickets.
**u029 S15 mobile_plan_purchase** — slots: what you want: compare mobile phone plans and pick a cheaper | your current carrier: Tandem Mobile | your current plan's data: unlimited in total for the whole p | how much data you use: about 3 GB a month | your monthly bill: about $85 | how many lines on the plan: 2 (you and your husband) | why: you want more data
- User: Can you help me compare mobile phone plans and pick a cheaper or better one?
- Assistant: Got it. How much do you pay each month now?
- User: Right now I have an unlimited data plan for the whole plan — not per line — and I pay about $85 a month. It's for two lines: my husband and me.
- Assistant: Sure. Which carrier are you with now?
- User: We're with Tandem Mobile. I use about 3 GB a month, but I'd like more data.
- Assistant: Here is what I'll look for: currently with Tandem Mobile; current plan unlimited; about 3 GB used a month; about $85 a month now; for 2 lines; you want more data.
- memory m006 ×3 [registered; pref:diet]: “User is vegetarian.” ← “I'm vegetarian.”
- memory m026 ×2 [registered; fact:plan_data]: “User's current phone plan has unlimited data for two lines.” ← “Our plan has unlimited data total for both lines”
- memory m025 ×2 [registered; -]: “User is considering changing their phone plan due to a recent increase in the bill.” ← “Hey, I want to check if I should change my phone plan. The bill went up recently”
- memory m021 ×1 [registered; pref:seating]: “User prefers seated venues over standing ones.” ← “I prefer seated venues”
- memory m013 ×1 [registered; -]: “User wants to reserve a table for a dinner out on Monday, the 19th of January, around 7:00 pm.” ← “Reserve a table for a dinner out on Monday, the 19th of January, about 7:00 pm.”

## u030

**u030 S11 concert_ticket_booking** — slots: what you want: change the seats or date of a concert booking | the venue of the show you hold seats for: Granite Arts Cente | the day: Sunday, 2 August (say the weekday and the day numbe | what you want changed: seats closer to the aisle | how many tickets: 1
- User: I want to change the seats or date of a concert booking. It's for Sunday, the 2nd of August.
- Assistant: Sure. Do you have a place in mind?
- User: I have a ticket for this Sunday, the 2nd of August, at the Granite Arts Center. It’s just me.
- Assistant: Got it. What would you like to change?
- User: I want to change my seats to ones closer to the aisle.
- Assistant: Here is what I'll look for: at Granite Arts Center; Sunday, the 2nd; seats closer to the aisle; for 1 ticket.
**u030 S12 fitness_class_booking** — slots: what you want: find a class time that fits your week and boo | the class you want to try: swimming | the day: Tuesday, 11 August (say the weekday and the day num | the day: Sunday, 16 August (say the weekday and the day numb | a time preference: you prefer afternoon events and being hom
- User: Find a swimming class time that fits my week and book a trial session. I want to try Tuesday, the 11th of August, or Sunday, the 16th of August.
- Assistant: Thanks. What time of day suits you best?
- User: I prefer afternoon events and being home by 9 pm.
- Assistant: Here is what I'll look for: a swimming class; Tuesday, the 11th; Sunday, the 16th; preferring afternoon events and being home by 9 pm.
- memory m003 ×3 [registered; fact:monthly_use_gb]: “User uses about 22 GB of data per month.” ← “I use about 22 GB a month.”
- memory m021 ×1 [registered; -]: “User wants to stay in a vacation rental for the weekend.” ← “I want a vacation rental for this weekend—Friday the 15th to Sunday the 17th.”
- memory m016 ×2 [registered; pref:diet]: “User is vegetarian.” ← “I'm vegetarian.”
- memory m007 ×1 [registered; person:friend, person:self]: “User has a dinner reservation at Stone Oven House for Tuesday, the 17th, at 8:30 pm for 2 people.” ← “It’s currently set for 8:30 pm on Tuesday, the 17th, for 2 people.”
- memory m014 ×1 [registered; -]: “User added bananas, apples, rice, and lentils to their Sunday, 22nd grocery order for the evening delivery slot.” ← “Add bananas, apples, rice, and lentils to the Sunday, 22nd grocery order for the evening delivery slot.”
