# Our inferencer on SynthPAI (age)

model: qwen3:32b, thinking on, temperature 0, same reasoning-first prompt as the dialogue inferencer; today = 2024-04-15. Age correct = within 5 years (SynthPAI's rule). Probabilities uncalibrated.

| subset | n | within 5 years | age-group accuracy | within 1 group | mean abs. error (years) | RPS |
|---|---|---|---|---|---|---|
| all users | 299 | 40.8% | 41.8% | 82.3% | 11.2 | 0.115 |
| human-verified subset (paper's evaluation set) | 155 | 58.1% | 49.0% | 91.6% | 7.4 | 0.096 |

Reference: SynthPAI paper, GPT-4 age accuracy on the human-verified set: 69.4%.
Human annotators attempted an age estimate for 171/299 users; at least one of their estimates was within 5 years for 155 (90.6% of attempted).

## By true age group (all users)

| group | n | within 5 years | group accuracy | within 1 |
|---|---|---|---|---|
| 18-24 | 30 | 56.7% | 20.0% | 93.3% |
| 25-34 | 90 | 70.0% | 71.1% | 98.9% |
| 35-44 | 62 | 53.2% | 71.0% | 100.0% |
| 45-54 | 60 | 5.0% | 10.0% | 85.0% |
| 55-64 | 43 | 9.3% | 7.0% | 25.6% |
| 65+ | 14 | 14.3% | 14.3% | 35.7% |
