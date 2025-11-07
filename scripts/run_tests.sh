#!/usr/bin/env bash
# QueueCTL_RamaSwetha - Full automated test & edge-case validation
# Author: Rama Swetha
# Date: 2025-11-07

set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PY=${PY:-python3}

cd "$ROOT"

echo "=============================================================="
echo " Cleaning environment..."
echo "=============================================================="
rm -f qctl.db qctl.pid
rm -rf logs || true
mkdir -p logs

# ------------------------------------------------------------
echo
echo "=============================================================="
echo "  Test 1: Enqueue basic success & failing jobs"
echo "=============================================================="
$PY -m queuectl_ramaswetha.cli enqueue '{"id":"job-success","command":"echo hello from job-success"}'
$PY -m queuectl_ramaswetha.cli enqueue '{"id":"job-fail","command":"bash -c \"exit 2\"","max_retries":2}'

# ------------------------------------------------------------
echo
echo "=============================================================="
echo "  Test 2: Enqueue invalid command (should fail & move to DLQ)"
echo "=============================================================="
$PY -m queuectl_ramaswetha.cli enqueue '{"id":"job-invalid","command":"nonexistent_cmd"}'

# ------------------------------------------------------------
echo
echo "=============================================================="
echo "  Test 3: Enqueue duplicate job ID (should raise DB error)"
echo "=============================================================="
set +e
$PY -m queuectl_ramaswetha.cli enqueue '{"id":"job-success","command":"echo duplicate"}'
if [ $? -ne 0 ]; then
  echo " Duplicate job ID correctly rejected"
else
  echo " Duplicate job ID allowed (unexpected)"
fi
set -e

# ------------------------------------------------------------
echo
echo "=============================================================="
echo " ️ Test 4: Change backoff configuration"
echo "=============================================================="
$PY -m queuectl_ramaswetha.cli config set backoff_base 3
echo "Backoff base now set to:"
$PY -m queuectl_ramaswetha.cli config get backoff_base

# ------------------------------------------------------------
echo
echo "=============================================================="
echo "  Test 5: Start workers (2 workers)"
echo "=============================================================="
$PY -m queuectl_ramaswetha.cli worker start --count 2 &

sleep 3
echo
echo "Status after startup:"
$PY -m queuectl_ramaswetha.cli status

# ------------------------------------------------------------
echo
echo "=============================================================="
echo " ⏱️ Test 6: Allow workers to process jobs (including retries)"
echo "=============================================================="
sleep 10

echo
echo "All jobs after processing:"
$PY -m queuectl_ramaswetha.cli list

# ------------------------------------------------------------
echo
echo "=============================================================="
echo "  Test 7: Stop workers gracefully"
echo "=============================================================="
$PY -m queuectl_ramaswetha.cli worker stop
sleep 2

# ------------------------------------------------------------
echo
echo "=============================================================="
echo "  Test 8: Restart worker (persistence check)"
echo "=============================================================="
$PY -m queuectl_ramaswetha.cli worker start --count 1 &
sleep 3
$PY -m queuectl_ramaswetha.cli status

# ------------------------------------------------------------
echo
echo "=============================================================="
echo "  Test 9: Check DLQ (dead jobs)"
echo "=============================================================="
$PY -m queuectl_ramaswetha.cli dlq list

DEAD_ID=$($PY - <<PY
import sqlite3
c=sqlite3.connect("qctl.db")
r=c.execute("SELECT id FROM jobs WHERE state='dead' LIMIT 1").fetchone()
print(r[0] if r else "")
PY
)

if [ -n "$DEAD_ID" ]; then
  echo "Found dead job: $DEAD_ID"
  echo "Retrying DLQ job..."
  $PY -m queuectl_ramaswetha.cli dlq retry "$DEAD_ID"
  sleep 2
  echo "Listing pending jobs after DLQ retry:"
  $PY -m queuectl_ramaswetha.cli list --state pending
else
  echo "No DLQ jobs found."
fi

# ------------------------------------------------------------
echo
echo "=============================================================="
echo "  Test 10: Purge completed jobs"
echo "=============================================================="
$PY -m queuectl_ramaswetha.cli purge --completed
echo "Remaining jobs:"
$PY -m queuectl_ramaswetha.cli list

# ------------------------------------------------------------
echo
echo "=============================================================="
echo "  All automated tests completed!"
echo "Check ./logs/ for job logs and qctl.db for persisted jobs."
echo "=============================================================="

