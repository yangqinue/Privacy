#!/bin/bash
# dev_v2 run order: dev seed 0 first (early look, uncalibrated), then the shadow calibration set,
# then dev seeds 1 and 2. The temperature is fitted on shadow data only (calibrate.py), never on dev.
set -u
cd "$(dirname "$0")"
SERVERS=${SERVERS:-http://localhost:11436=4,http://localhost:11437=4,http://localhost:11434=1}
python3 -u run_dev2.py --seed 0 --servers "$SERVERS"
python3 -u run_dev2.py --split shadow_calib --seed 100 --out ../runs/dev_v2/shadow --servers "$SERVERS"
python3 -u run_dev2.py --seed 1 --servers "$SERVERS"
python3 -u run_dev2.py --seed 2 --servers "$SERVERS"
