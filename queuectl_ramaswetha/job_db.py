# JobDatabase: persistence layer using SQLite
# Author: Rama Swetha
# Notes: Uses transactions to safely claim jobs to avoid duplicate processing.
# Added columns: priority, timeout, run_at to support bonus features.

import sqlite3
import os
from datetime import datetime, timezone, timedelta
from .utils import utcnow_iso

DB_FILE = os.getenv("QCTL_DB", "qctl.db")

class JobDatabase:
    def __init__(self, path=DB_FILE):
        self.path = path
        # isolation_level=None => autocommit; we'll manage transactions manually
        self.conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            command TEXT NOT NULL,
            state TEXT NOT NULL,
            attempts INTEGER NOT NULL,
            max_retries INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            run_at TEXT,
            last_error TEXT,
            worker_id TEXT,
            priority INTEGER DEFAULT 0,
            timeout INTEGER DEFAULT 30
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)
        # default configs
        if not self.get_config("backoff_base"):
            self.set_config("backoff_base", "2")
        if not self.get_config("default_max_retries"):
            self.set_config("default_max_retries", "3")

    # ----- Config helpers -----
    def set_config(self, key, value):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO config(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
        self.conn.commit()

    def get_config(self, key):
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM config WHERE key=?", (key,))
        r = cur.fetchone()
        return r["value"] if r else None

    # ----- Jobs CRUD -----
    def enqueue(self, job: dict):
        """
        Enqueue a job dict. Expected keys: id, command.
        Optional keys: max_retries, run_at (ISO str), priority (int), timeout (int)
        """
        now = utcnow_iso()
        cur = self.conn.cursor()
        job_state = job.get("state", "pending")
        attempts = int(job.get("attempts", 0))
        max_retries = int(job.get("max_retries", int(self.get_config("default_max_retries") or 3)))
        run_at = job.get("run_at", None)
        priority = int(job.get("priority", 0))
        timeout = int(job.get("timeout", 30))
        cur.execute("""
            INSERT INTO jobs(id, command, state, attempts, max_retries, created_at, updated_at, run_at, last_error, worker_id, priority, timeout)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            job["id"], job["command"], job_state, attempts, max_retries,
            now, now, run_at, job.get("last_error"), None, priority, timeout
        ))
        self.conn.commit()

    def list_jobs(self, state=None):
        cur = self.conn.cursor()
        if state:
            cur.execute("SELECT * FROM jobs WHERE state=? ORDER BY created_at ASC", (state,))
        else:
            cur.execute("SELECT * FROM jobs ORDER BY created_at ASC")
        return [dict(r) for r in cur.fetchall()]

    def job_counts(self):
        cur = self.conn.cursor()
        cur.execute("SELECT state, COUNT(*) as cnt FROM jobs GROUP BY state")
        return {r["state"]: r["cnt"] for r in cur.fetchall()}

    def get_job(self, job_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        r = cur.fetchone()
        return dict(r) if r else None

    # Atomic claim: find one pending job (run_at <= now or NULL) and set to 'processing' with worker_id
    def claim_job(self, worker_id):
        cur = self.conn.cursor()
        now = utcnow_iso()
        try:
            cur.execute("BEGIN IMMEDIATE")  # acquire write lock for safe update
            cur.execute("""
                SELECT id FROM jobs
                WHERE state='pending' AND (run_at IS NULL OR run_at <= ?)
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
            """, (now,))
            row = cur.fetchone()
            if not row:
                cur.execute("COMMIT")
                return None
            job_id = row["id"]
            cur.execute("""
                UPDATE jobs SET state='processing', worker_id=?, updated_at=? WHERE id=? AND state='pending'
            """, (worker_id, now, job_id))
            if cur.rowcount == 0:
                cur.execute("ROLLBACK")
                return None
            cur.execute("COMMIT")
            cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
            return dict(cur.fetchone())
        except Exception:
            cur.execute("ROLLBACK")
            raise

    def update_on_success(self, job_id):
        cur = self.conn.cursor()
        now = utcnow_iso()
        cur.execute("UPDATE jobs SET state='completed', updated_at=?, worker_id=NULL WHERE id=?", (now, job_id))
        self.conn.commit()

    def update_on_failure(self, job_id, error_message):
        cur = self.conn.cursor()
        cur.execute("SELECT attempts, max_retries FROM jobs WHERE id=?", (job_id,))
        row = cur.fetchone()
        if not row:
            return
        attempts = row["attempts"] + 1
        max_retries = row["max_retries"]
        now = utcnow_iso()
        if attempts > max_retries:
            # move to dead
            cur.execute("""
                UPDATE jobs SET state='dead', attempts=?, last_error=?, updated_at=?, worker_id=NULL WHERE id=?
            """, (attempts, error_message, now, job_id))
        else:
            # schedule next attempt with exponential backoff
            base = int(self.get_config("backoff_base") or 2)
            delay = base ** attempts
            next_run = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
            cur.execute("""
                UPDATE jobs SET state='pending', attempts=?, last_error=?, run_at=?, updated_at=?, worker_id=NULL WHERE id=?
            """, (attempts, error_message, next_run, now, job_id))
        self.conn.commit()

    def retry_dead_job(self, job_id):
        cur = self.conn.cursor()
        now = utcnow_iso()
        cur.execute("UPDATE jobs SET state='pending', attempts=0, run_at=NULL, updated_at=?, last_error=NULL WHERE id=? AND state='dead'", (now, job_id))
        self.conn.commit()
        return cur.rowcount > 0

    def purge_completed(self):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM jobs WHERE state='completed'")
        deleted = cur.rowcount
        self.conn.commit()
        return deleted

    def get_metrics(self):
        cur = self.conn.cursor()
        total = cur.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        completed = cur.execute("SELECT COUNT(*) FROM jobs WHERE state='completed'").fetchone()[0]
        failed = cur.execute("SELECT COUNT(*) FROM jobs WHERE state='failed'").fetchone()[0]
        dead = cur.execute("SELECT COUNT(*) FROM jobs WHERE state='dead'").fetchone()[0]
        avg = cur.execute("""
            SELECT AVG((julianday(updated_at) - julianday(created_at)) * 86400.0)
            FROM jobs
            WHERE state='completed'
        """).fetchone()[0]
        return {"total": total, "completed": completed, "failed": failed, "dead": dead, "avg_duration": avg}

