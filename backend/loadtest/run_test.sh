#!/usr/bin/env bash
# Запуск навантажувального тесту з одночасним збором CPU/RAM.
# Використання (з папки backend):
#   bash loadtest/run_test.sh <назва_прогону> <користувачів> <розгін_кор/с> <тривалість> [host]
# Приклад: bash loadtest/run_test.sh baseline 100 10 120s http://127.0.0.1:8000
set -euo pipefail
NAME=${1:?назва}; USERS=${2:-100}; RATE=${3:-10}; TIME=${4:-120s}; HOST=${5:-http://127.0.0.1:8000}
OUT=loadtest/results; mkdir -p "$OUT"
python loadtest/monitor.py "$OUT/$NAME-monitor.csv" 2 &
MON=$!
trap 'kill $MON 2>/dev/null || true' EXIT
locust -f loadtest/locustfile.py --headless --host "$HOST" \
  -u "$USERS" -r "$RATE" -t "$TIME" --csv "$OUT/$NAME" --csv-full-history \
  --only-summary --exit-code-on-error 0
kill $MON 2>/dev/null || true
python loadtest/analyze.py summary "$OUT/$NAME" "$OUT/$NAME-monitor.csv"
