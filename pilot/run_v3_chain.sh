#!/bin/bash
# dev_v3: waits for the dev_v2 chain to finish (it needs dev_v2 openings), then runs the seeded adaptive mode
# for seeds 0-2 and re-judges the dev_v2 dialogues with the v3 judge.
set -u
cd "$(dirname "$0")"
SERVERS=${SERVERS:-http://localhost:11436=4,http://localhost:11437=4,http://localhost:11434=1}
while pgrep -f "run_v2_chain.sh" > /dev/null; do sleep 60; done
for s in 0 1 2; do python3 -u run_dev3.py --seed $s --servers "$SERVERS"; done
python3 -u rejudge_v3.py --servers "$SERVERS"
