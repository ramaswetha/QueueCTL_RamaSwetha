---

# **QueueCTL_RamaSwetha**

**QueueCTL** is a command-line (CLI) based background job queue system built in **Python 3.12**.
It allows you to enqueue background jobs, process them with multiple worker processes, automatically retry failed jobs with **exponential backoff**, and maintain a **Dead Letter Queue (DLQ)** for permanently failed tasks.

It also includes a **real-time web dashboard** for monitoring jobs, priorities, metrics, and system state — all with **dark/light mode support**.

The system uses **SQLite** for persistent job storage, ensuring that no jobs are lost across restarts.

---

## **Setup Instructions**

To run QueueCTL locally:

1️⃣ **Clone the repository**

```bash
git clone https://github.com/ramaswetha/QueueCTL_RamaSwetha.git
cd QueueCTL_RamaSwetha
```

2️⃣ **Create a virtual environment**

```bash
python3 -m venv .venv
```

3️⃣ **Activate the environment**

* On macOS/Linux:

  ```bash
  source .venv/bin/activate
  ```
* On Windows:

  ```bash
  .venv\Scripts\activate
  ```

4️⃣ No external dependencies are needed — QueueCTL runs entirely on **Python standard libraries**.

5️⃣ **Run commands:**

```bash
python -m queuectl_ramaswetha.cli <command>
```

6️⃣ Or run the complete test suite:

```bash
./scripts/run_tests.sh
```

---

## 💻 **Usage Examples**

### Enqueue a new job:

```bash
python -m queuectl_ramaswetha.cli enqueue '{"id":"job1","command":"echo hello world"}'
```

### Start worker processes:

```bash
python -m queuectl_ramaswetha.cli worker start --count 2
```

### Stop all workers gracefully:

```bash
python -m queuectl_ramaswetha.cli worker stop
```

### View job and worker status:

```bash
python -m queuectl_ramaswetha.cli status
```

### List jobs by state:

```bash
python -m queuectl_ramaswetha.cli list --state pending
```

### View Dead Letter Queue (DLQ):

```bash
python -m queuectl_ramaswetha.cli dlq list
```

### Retry a DLQ job:

```bash
python -m queuectl_ramaswetha.cli dlq retry job1
```

### Adjust configuration:

```bash
python -m queuectl_ramaswetha.cli config set max-retries 3
python -m queuectl_ramaswetha.cli config set backoff_base 2
python -m queuectl_ramaswetha.cli config get backoff_base
```

### Purge completed jobs:

```bash
python -m queuectl_ramaswetha.cli purge --completed
```

All job logs are stored in the `./logs/` directory.
The `qctl.db` SQLite file holds persistent job data, states, and configuration.

---

## 🌐 **Web Dashboard**

QueueCTL provides a simple **Flask-based web dashboard** to visualize the queue in real time.

### Start the dashboard:

```bash
python -m queuectl_ramaswetha.dashboard
```

Then visit:
 [http://localhost:8080](http://localhost:8080)

The dashboard shows:

* Total jobs by state (pending, processing, completed, failed, dead)
* Job priority, timeout, and retry counts
* Automatic live refresh every 5 seconds
* **Dark/Light mode toggle** 

---

## **Architecture Overview**

QueueCTL has three main components:

* **CLI Interface:** Handles all user commands (enqueue, worker, DLQ, config).
* **SQLite Database:** Stores jobs, states, retries, priorities, and scheduling info persistently.
* **Worker Processes:** Poll the database, claim pending jobs atomically, and execute commands via Python’s subprocess module.

### Job Lifecycle:

1. **Pending** → waiting to be picked up
2. **Processing** → being executed by a worker
3. **Completed** → finished successfully
4. **Failed** → temporarily failed (retryable)
5. **Dead** → permanently failed (moved to DLQ)

Workers respect **exponential backoff** for retries (`delay = base ^ attempts`) and **graceful shutdown** (finishing current job before stopping).

---

## **Extra Features Implemented**

**Job Timeout Handling** — each job has a configurable timeout (default 30s).
**Job Priority Queues** — higher priority jobs are executed first.
**Scheduled/Delayed Jobs (`run_at`)** — run jobs at a future timestamp.
**Job Output Logging** — each job writes detailed logs under `logs/job_<id>.log`.
**Metrics & Execution Stats** — total, completed, failed, and dead counts visible via CLI and dashboard.
**Web Dashboard with Dark Mode** — real-time monitoring interface with theme toggle.

---

## **Assumptions & Trade-offs**

* Focused on **local reliability and simplicity** rather than distributed scalability.
* SQLite chosen for persistence — lightweight and no setup required.
* Single-node, multi-process architecture (easy to extend to multi-host later).
* Logging is file-based for transparency.
* Prioritizes readability, modularity, and correctness over complexity.

---

## **Testing Instructions**

Run all automated tests with:

```bash
./scripts/run_tests.sh
```

This verifies:

* Successful and failing job execution
* Retry + exponential backoff
* Dead Letter Queue handling
* Duplicate ID rejection
* Persistence across restarts
* Graceful worker shutdown

You can also manually test each command via the CLI or monitor progress on the dashboard.

---

## **Demo Recording**

Watch the complete CLI and Dashboard demo here:
🎬 [https://drive.google.com/file/d/1Ow803r0Bt8oAvw5VYsbXSU_mL_ct2CSG/view?usp=sharing](https://drive.google.com/file/d/1Ow803r0Bt8oAvw5VYsbXSU_mL_ct2CSG/view?usp=sharing)

---

## **Checklist Before Submission**

* All required commands functional
* Jobs persist after restart
* Retry and exponential backoff implemented
* DLQ operational and retryable
* CLI user-friendly and documented
* Modular, maintainable code structure
* Includes automated test script
* Dashboard functional with live updates and dark mode

---

## **Author**

Developed by **Rama Swetha Ponnaganti** as part of the **FLAM Backend Developer Internship Assignment**.
This project demonstrates expertise in concurrent background processing, persistence, fault tolerance, configuration management, and UI monitoring using pure Python.

