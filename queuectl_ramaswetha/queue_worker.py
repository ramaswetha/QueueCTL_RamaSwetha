# QueueWorker: worker processes that claim and run jobs
# Author: Rama Swetha

import os
import signal
import subprocess
import time
import uuid
from multiprocessing import Process
from datetime import datetime, timezone
from .job_db import JobDatabase
from .utils import utcnow_iso

PIDFILE = os.getenv("QCTL_PIDFILE", "qctl.pid")
LOG_DIR = os.getenv("QCTL_LOGDIR", "logs")

class QueueWorker:
    """
    Polls the DB for pending jobs, claims them atomically, runs the command,
    and updates status. Graceful shutdown implemented by listening to SIGTERM/SIGINT.
    """

    def __init__(self, name=None, poll_interval=1):
        # Do NOT open the DB connection here (to avoid pickle errors)
        self.name = name or f"qworker-{uuid.uuid4().hex[:6]}"
        self.poll_interval = poll_interval
        self._stopping = False

    def _log_job(self, job_id, text):
        os.makedirs(LOG_DIR, exist_ok=True)
        path = os.path.join(LOG_DIR, f"job_{job_id}.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{utcnow_iso()}] {text}\n")

    def _execute(self, command, timeout=None):
        """Run the job command with timeout handling."""
        try:
            proc = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout or 30,
            )
            out = proc.stdout.decode("utf-8", errors="replace")
            err = proc.stderr.decode("utf-8", errors="replace")
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            return 1, "", f"Job timed out after {timeout or 30} seconds"
        except Exception as ex:
            return 1, "", str(ex)

    def _handle_signal(self, signum, frame):
        print(f"[{self.name}] Received signal {signum}. Will stop after current job.")
        self._stopping = True

    def run_forever(self):
        """Main loop that runs inside each worker subprocess."""
        # Initialize DB here (inside child process)
        db = JobDatabase()
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        print(f"[{self.name}] started (pid={os.getpid()})")

        while not self._stopping:
            job = db.claim_job(self.name)
            if not job:
                time.sleep(self.poll_interval)
                continue

            # Respect scheduled jobs (run_at)
            run_at = job.get("run_at")
            if run_at:
                try:
                    # parse ISO formatted time (with or without offset)
                    run_dt = datetime.fromisoformat(run_at)
                    now = datetime.now(timezone.utc)
                    # normalize run_dt to UTC-aware for comparison
                    if run_dt.tzinfo is None:
                        run_dt = run_dt.replace(tzinfo=timezone.utc)
                    run_dt_utc = run_dt.astimezone(timezone.utc)
                    if run_dt_utc > now:
                        # not yet time to run this job; release CPU and continue
                        time.sleep(self.poll_interval)
                        # Note: the job remains in pending state but was claimed; however claim_job selects only pending.
                        # To keep behavior consistent, continue here (worker will pick next job next loop)
                        continue
                except Exception:
                    # if parsing fails, ignore and proceed
                    pass

            job_id = job["id"]
            cmd = job["command"]
            attempts = job.get("attempts", 0)
            timeout = job.get("timeout", 30)  # default 30s

            print(f"[{self.name}] claimed job {job_id} (attempts={attempts}) cmd='{cmd}' (timeout={timeout}s)")
            self._log_job(job_id, f"Worker {self.name} executing: {cmd} (timeout={timeout}s)")
            code, out, err = self._execute(cmd, timeout=timeout)
            if code == 0:
                self._log_job(job_id, f"SUCCESS stdout: {out.strip()}")
                db.update_on_success(job_id)
                print(f"[{self.name}] job {job_id} completed")
            else:
                msg = f"exit={code}; stderr={err.strip() or out.strip()}"
                self._log_job(job_id, f"FAIL {msg}")
                db.update_on_failure(job_id, msg)
                print(f"[{self.name}] job {job_id} failed: {msg}")
        print(f"[{self.name}] stopping gracefully")


def start_workers(count=1, pidfile=PIDFILE):
    """Start multiple worker processes."""
    procs = []
    for i in range(count):
        name = f"qworker-{i+1}"
        p = Process(target=QueueWorker(name=name).run_forever, name=name)
        p.start()
        procs.append(p)

    with open(pidfile, "w") as f:
        for p in procs:
            f.write(str(p.pid) + "\n")

    print(f"Started {len(procs)} workers (pids in {pidfile})")
    return procs


def stop_workers(pidfile=PIDFILE):
    """Gracefully stop workers by sending SIGTERM."""
    if not os.path.exists(pidfile):
        print("No pidfile found. No workers to stop.")
        return
    with open(pidfile, "r") as f:
        pids = [int(line.strip()) for line in f if line.strip()]
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to pid {pid}")
        except ProcessLookupError:
            print(f"Process {pid} not found")
    try:
        os.remove(pidfile)
    except OSError:
        pass
    print("Stop signals sent. Workers will exit after finishing current job.")

