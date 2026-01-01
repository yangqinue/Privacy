# dev_v3 results (adaptive_seeded, compared with dev_v2 modes)

seeds: [0, 1, 2]; people: 30; conversations: 360; calibration from dev_v2: T=5.2784, delta=0.001
v3 judge available for 360/360 conversations (rest: original dev_v2 judge)

## Mode means (final turn)

| mode | RPS | expected distance | accuracy | within 1 | strong cue leaked | asked about the past (msgs/conv) | asked when an event happened (convs) | mean length |
|---|---|---|---|---|---|---|---|---|
| benign | 0.191 | 1.86 | 0.23 | 0.51 | 0/90 | 0.0 | 0/90 | 3.8 |
| fixed | 0.176 | 1.74 | 0.29 | 0.62 | 18/90 | 1.1 | 1/90 | 6.0 |
| adaptive | 0.170 | 1.74 | 0.34 | 0.71 | 12/90 | 1.2 | 1/90 | 6.4 |
| adaptive_seeded | 0.171 | 1.73 | 0.26 | 0.73 | 17/90 | 1.6 | 4/90 | 6.7 |

## Paired comparisons (negative = A leaks more)

| comparison | Δ RPS (primary) | Δ expected distance | Δ accuracy | Δ within-1 | RPS win / tie / loss for A |
|---|---|---|---|---|---|
| adaptive_seeded - fixed | -0.005 [-0.017, +0.011] | -0.006 [-0.069, +0.067] | -0.033 [-0.173, +0.086] | +0.111 [-0.012, +0.232] | 17 / 5 / 8 |
| adaptive_seeded - adaptive | +0.001 [-0.013, +0.014] | -0.006 [-0.081, +0.065] | -0.089 [-0.177, -0.011] | +0.022 [-0.095, +0.161] | 10 / 8 / 12 |
| adaptive_seeded - benign | -0.020 [-0.034, -0.004] | -0.134 [-0.205, -0.051] | +0.022 [-0.123, +0.161] | +0.222 [+0.026, +0.419] | 18 / 5 / 7 |
| fixed - benign | -0.015 [-0.033, +0.003] | -0.127 [-0.211, -0.038] | +0.056 [-0.080, +0.198] | +0.111 [-0.040, +0.278] | 16 / 6 / 8 |
| adaptive - benign | -0.021 [-0.035, -0.006] | -0.127 [-0.192, -0.058] | +0.111 [-0.022, +0.253] | +0.200 [+0.067, +0.323] | 18 / 7 / 5 |

## Per seed (Δ RPS)

| comparison | seed 0 | seed 1 | seed 2 |
|---|---|---|---|
| adaptive_seeded - fixed | -0.003 [-0.021, +0.015] | -0.006 [-0.024, +0.017] | -0.005 [-0.030, +0.020] |
| adaptive_seeded - adaptive | -0.008 [-0.042, +0.018] | -0.010 [-0.034, +0.015] | +0.020 [+0.004, +0.041] |
| adaptive_seeded - benign | -0.024 [-0.046, -0.005] | -0.016 [-0.041, +0.010] | -0.018 [-0.032, -0.001] |
| fixed - benign | -0.021 [-0.045, -0.001] | -0.011 [-0.031, +0.008] | -0.013 [-0.035, +0.012] |
| adaptive - benign | -0.016 [-0.038, +0.008] | -0.007 [-0.025, +0.013] | -0.038 [-0.058, -0.021] |

## Event-time questions (policy B)

- adaptive_seeded, asked when an event happened: n=4, final RPS 0.158, strong cue leaked 0/4
- adaptive_seeded, did not ask: n=86, final RPS 0.172, strong cue leaked 17/86

adaptive_seeded - fixed, excluding seeded dialogues with event-time questions (descriptive): -0.004 [-0.017, +0.011]

## Agent behaviour (v3 judge)

| mode | explicit age request | ambiguous | probing msgs/conv | booking ok |
|---|---|---|---|---|
| benign | 0/90 | 0/90 | 0.0 | 81/90 |
| fixed | 0/90 | 0/90 | 2.8 | 86/90 |
| adaptive | 0/90 | 0/90 | 1.8 | 82/90 |
| adaptive_seeded | 0/90 | 1/90 | 2.2 | 80/90 |
