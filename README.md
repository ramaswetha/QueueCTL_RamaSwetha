QueueCTL_RamaSwetha

QueueCTL is a command-line (CLI) based background job queue system built in Python 3.12.
It allows you to enqueue background jobs, process them with multiple worker processes, automatically retry failed jobs using exponential backoff, and maintain a Dead Letter Queue (DLQ) for permanently failed tasks.
The system includes persistent job storage using SQLite so that no jobs are lost across restarts.

Setup Instructions

To run QueueCTL locally, follow these steps:

Clone the repository using
git clone https://github.com/<your-username>/QueueCTL_RamaSwetha.git
and navigate to the project folder using
cd QueueCTL_RamaSwetha

Create a virtual environment using
python3 -m venv .venv

Activate the virtual environment:
On macOS or Linux, run source .venv/bin/activate.
On Windows, run .venv\Scripts\activate.

This project uses only Python standard libraries, so no external packages need to be installed.

Once the environment is ready, you can run CLI commands using
python -m queuectl_ramaswetha.cli <command>
or execute the test script with
./scripts/run_tests.sh


Usage Examples

Below are some example commands that demonstrate how QueueCTL works:

To enqueue a new job:
python -m queuectl_ramaswetha.cli enqueue '{"id":"job1","command":"echo hello world"}'

To start worker processes:
python -m queuectl_ramaswetha.cli worker start --count 2

To stop all running workers gracefully:
python -m queuectl_ramaswetha.cli worker stop

To check the current status of all jobs and workers:
python -m queuectl_ramaswetha.cli status

To list jobs by their state (for example, pending jobs):
python -m queuectl_ramaswetha.cli list --state pending

To view jobs in the Dead Letter Queue (DLQ):
python -m queuectl_ramaswetha.cli dlq list

To retry a specific job from the DLQ:
python -m queuectl_ramaswetha.cli dlq retry job1

To change configuration settings such as retry count or backoff base:
python -m queuectl_ramaswetha.cli config set max-retries 3
and
python -m queuectl_ramaswetha.cli config set backoff_base 2

To view a configuration value:
python -m queuectl_ramaswetha.cli config get backoff_base

To remove all completed jobs from the queue:
python -m queuectl_ramaswetha.cli purge --completed

All logs for each job are saved in the ./logs/ directory, and the SQLite database file qctl.db stores job states and configurations persistently.


Architecture Overview

QueueCTL consists of three main components — the CLI interface, the SQLite job database, and worker processes.
When a job is enqueued, it is stored in the database with its command, state, and retry information. Workers, running as separate processes, continuously poll for pending jobs and claim them atomically to avoid duplicate execution. Each job is executed via Python’s subprocess module, and its exit code determines whether it completes successfully or fails.

Failed jobs are retried automatically using exponential backoff (delay = base ^ attempts). Once the maximum retry limit is reached, the job moves to the Dead Letter Queue (DLQ).
All job states — pending, processing, completed, failed, and dead — are stored persistently, allowing recovery after restarts. The system also supports graceful shutdown, ensuring workers finish their current job before stopping.


Assumptions and Trade-offs

QueueCTL prioritizes reliability, simplicity, and transparency over distributed scalability. SQLite was chosen for persistence because it is lightweight, requires no setup, and suits single-machine operation.
The system is intentionally single-node, with all workers sharing one local database file. While this limits horizontal scalability, it ensures deterministic behavior and ease of maintenance.

The retry and backoff mechanisms are simple and predictable, and logging is file-based for clarity. The overall design focuses on readability and robustness rather than complex distributed coordination.


Testing Instructions

To verify the functionality of QueueCTL, a complete automated shell script is provided under scripts/run_tests.sh.
You can run it using the command:

./scripts/run_tests.sh

This script performs a full end-to-end test of the system. It enqueues both successful and failing jobs, tests automatic retries with exponential backoff, validates the Dead Letter Queue, checks duplicate job handling, verifies persistence after worker restarts, and ensures that workers shut down gracefully when stopped.

You can also manually test individual components by running CLI commands such as enqueue, status, dlq list, or config get to inspect the system’s state.
After running the tests, check the logs/ folder to view each job’s execution output and verify that the database file qctl.db contains the persisted job data.


Demo Recording

A short screen recording demonstrates the complete workflow of the system — including enqueuing jobs, starting workers, retries, DLQ movement, and configuration commands.

Watch the CLI demo here:
https://drive.google.com/file/d/1Ow803r0Bt8oAvw5VYsbXSU_mL_ct2CSG/view?usp=sharing


Author

Developed by Rama Swetha Ponnaganti as part of the FLAM assignment.
This project demonstrates understanding of concurrent job execution, persistence, fault tolerance, and CLI-based system design using pure Python.

