conda create -n antiskill python=3.11 -y
conda activate antiskill
pip install datasets

# AntiSkillBench

relational database
                  character
              ┌─────────────────┐
              │ character_id PK │
              │ age             │
              │ gender          │
              │ race            │
              │ occupation      │
              │ education       │
              │ personality     │
              │ big_five        │
              │ language_style  │
              └────────┬────────┘
                       │
                       ▼
                  question
              ┌─────────────────┐
              │ character_id FK │
              │ question_id     │
              │ question_type   │
              │ question        │
              └────────┬────────┘
                       │
                       ▼
                  dialogue
              ┌─────────────────┐
              │ character_id    │
              │ question        │
              │ dialogue        │
              └─────────────────┘

