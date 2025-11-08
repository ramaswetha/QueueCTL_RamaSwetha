#!/usr/bin/env python3
# CLI for QueueCTL_RamaSwetha
# Author: Rama Swetha

import argparse
import json
import os
import sys
from .job_db import JobDatabase
from .queue_worker import start_workers, stop_workers
from .utils import utcnow_iso
from datetime import datetime, timezone, timedelta

PIDFILE = os.getenv("QCTL_PIDFILE", "qctl.pid")

def cmd_enqueue(args):
    db = JobDatabase()
    # accept JSON string or path to file
    try:
        if os.path.exists(args.job_json):
            with open(args.job_json, "r", encoding="utf-8") as f:
                job = json.load(f)
        else:
            job = json.loads(args.job_json)
    except Exception as ex:
        print("Invalid JSON or file:", ex)
        return
    if "id" not in job or "command" not in job:
        print("Job must include 'id' and 'command'")
        return

    # allow --delay (seconds) to set run_at
    if args.delay and args.delay > 0:
        run_at = (datetime.now(timezone.utc) + timedelta(seconds=args.delay)).isoformat()
        job["run_at"] = run_at
    # allow explicit --run-at ISO string
    if args.run_at:
        job["run_at"] = args.run_at

    # priority and timeout
    if args.priority is not None:
        job["priority"] = int(args.priority)
    if args.timeout is not None:
        job["timeout"] = int(args.timeout)

    # set timestamps if not provided
    now = utcnow_iso()
    if "created_at" not in job:
        job["created_at"] = now
    if "updated_at" not in job:
        job["updated_at"] = now

    try:
        db.enqueue(job)
    except Exception as ex:
        print("Failed to enqueue job:", ex)
        return
    print(f"Enqueued job {job['id']} (command: {job['command']})")

def cmd_worker_start(args):
    start_workers(args.count)

def cmd_worker_stop(args):
    stop_workers()

def cmd_status(args):
    db = JobDatabase()
    counts = db.job_counts()
    print("Job counts:")
    for s in ["pending", "processing", "completed", "dead"]:
        print(f"  {s}: {counts.get(s, 0)}")
    if os.path.exists(PIDFILE):
        with open(PIDFILE, "r") as f:
            pids = [line.strip() for line in f if line.strip()]
        print("Active worker pids:", ", ".join(pids))
    else:
        print("Active worker pids: none")

def cmd_list(args):
    db = JobDatabase()
    rows = db.list_jobs(state=args.state)
    for r in rows:
        print(json.dumps(r, default=str))

def cmd_dlq_list(args):
    db = JobDatabase()
    rows = db.list_jobs(state="dead")
    for r in rows:
        print(json.dumps(r, default=str))

def cmd_dlq_retry(args):
    db = JobDatabase()
    ok = db.retry_dead_job(args.job_id)
    print("Retried" if ok else "No such dead job or already retried")

def cmd_config_set(args):
    db = JobDatabase()
    db.set_config(args.key, args.value)
    print("OK")

def cmd_config_get(args):
    db = JobDatabase()
    v = db.get_config(args.key)
    print(v if v is not None else "")

def cmd_purge_completed(args):
    db = JobDatabase()
    deleted = db.purge_completed()
    print(f"Deleted {deleted} completed jobs")

def cmd_metrics(args):
    db = JobDatabase()
    stats = db.get_metrics()
    print(f"Total jobs: {stats['total']}")
    print(f"Completed: {stats['completed']}")
    print(f"Failed: {stats['failed']}")
    print(f"Dead: {stats['dead']}")
    if stats['avg_duration'] is not None:
        print(f"Average execution time: {stats['avg_duration']:.2f}s")

def build_parser():
    p = argparse.ArgumentParser(prog="qctl", description="QueueCTL_RamaSwetha CLI")
    sub = p.add_subparsers(dest="cmd")

    enq = sub.add_parser("enqueue", help="Enqueue a job (JSON string or filename)")
    enq.add_argument("job_json", help='Job JSON or path to job file (must include id and command)')
    enq.add_argument("--delay", type=int, default=0, help="Delay in seconds before allowing job to run")
    enq.add_argument("--run-at", type=str, default=None, help="ISO time to run job at (e.g. 2025-11-07T12:00:00+00:00)")
    enq.add_argument("--priority", type=int, default=0, help="Job priority (higher runs first)")
    enq.add_argument("--timeout", type=int, default=30, help="Job timeout in seconds (default 30s)")
    enq.set_defaults(func=cmd_enqueue)

    worker = sub.add_parser("worker", help="Manage workers")
    wsub = worker.add_subparsers(dest="sub")
    ws = wsub.add_parser("start", help="Start workers (writes pidfile qctl.pid)")
    ws.add_argument("--count", type=int, default=1)
    ws.set_defaults(func=cmd_worker_start)
    wstop = wsub.add_parser("stop", help="Stop workers gracefully (reads pidfile)")
    wstop.set_defaults(func=cmd_worker_stop)

    status = sub.add_parser("status", help="Show status")
    status.set_defaults(func=cmd_status)

    lst = sub.add_parser("list", help="List jobs")
    lst.add_argument("--state", choices=["pending","processing","completed","dead"], default=None)
    lst.set_defaults(func=cmd_list)

    dlq = sub.add_parser("dlq", help="Dead Letter Queue commands")
    dsub = dlq.add_subparsers(dest="sub")
    dlist = dsub.add_parser("list")
    dlist.set_defaults(func=cmd_dlq_list)
    dretry = dsub.add_parser("retry")
    dretry.add_argument("job_id")
    dretry.set_defaults(func=cmd_dlq_retry)

    cfg = sub.add_parser("config", help="Get/Set config")
    cfgsub = cfg.add_subparsers(dest="sub")
    cset = cfgsub.add_parser("set")
    cset.add_argument("key")
    cset.add_argument("value")
    cset.set_defaults(func=cmd_config_set)
    cget = cfgsub.add_parser("get")
    cget.add_argument("key")
    cget.set_defaults(func=cmd_config_get)

    purge = sub.add_parser("purge", help="Purge completed jobs")
    purge.add_argument("--completed", action="store_true")
    purge.set_defaults(func=lambda args: cmd_purge_completed(args) if args.completed else print("use --completed"))

    metrics = sub.add_parser("metrics", help="Show job metrics")
    metrics.set_defaults(func=cmd_metrics)

    return p

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)

if __name__ == "__main__":
    main()

