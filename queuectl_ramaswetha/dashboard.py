# Enhanced Web Dashboard for QueueCTL_RamaSwetha with Dark Mode Toggle
# Author: Rama Swetha

from flask import Flask, render_template_string
from .job_db import JobDatabase

app = Flask(__name__)

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>QueueCTL Dashboard</title>
    <style>
        body {
            font-family: 'Inter', Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 40px;
            transition: background 0.3s, color 0.3s;
        }
        h1 {
            color: var(--accent-color);
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 20px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        th {
            background-color: var(--accent-color);
            color: white;
            padding: 10px;
            text-align: left;
        }
        td {
            border-bottom: 1px solid var(--border-color);
            padding: 8px;
        }
        tr:nth-child(even) {
            background-color: var(--row-alt);
        }
        .stats {
            display: flex;
            gap: 16px;
            margin-bottom: 20px;
        }
        .stat-box {
            background-color: var(--stat-bg);
            border: 1px solid var(--stat-border);
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 500;
        }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            color: white;
        }
        .completed { background-color: #22c55e; }
        .processing { background-color: #facc15; color: black; }
        .pending { background-color: #9ca3af; }
        .failed, .dead { background-color: #ef4444; }

        /* Light theme variables */
        :root {
            --bg-color: #f8fafc;
            --text-color: #333;
            --accent-color: #00853f;
            --border-color: #ddd;
            --row-alt: #f2f2f2;
            --stat-bg: #e9f8ee;
            --stat-border: #b3e6c2;
        }

        /* Dark theme overrides */
        body.dark {
            --bg-color: #0d1117;
            --text-color: #e6edf3;
            --accent-color: #10b981;
            --border-color: #30363d;
            --row-alt: #161b22;
            --stat-bg: #1e2a22;
            --stat-border: #256f4d;
        }

        .toggle {
            position: absolute;
            top: 20px;
            right: 30px;
            background: var(--accent-color);
            border: none;
            color: white;
            padding: 8px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
        }
        .toggle:hover {
            opacity: 0.9;
        }
    </style>
    <script>
        // Auto-refresh every 5 seconds
        setInterval(() => { window.location.reload(); }, 5000);

        // Dark mode toggle
        function toggleTheme() {
            const body = document.body;
            const isDark = body.classList.toggle('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            document.getElementById('themeBtn').innerText = isDark ? '☀️ Light Mode' : '🌙 Dark Mode';
        }

        // Remember theme on load
        window.onload = function() {
            const saved = localStorage.getItem('theme');
            if (saved === 'dark') {
                document.body.classList.add('dark');
                document.getElementById('themeBtn').innerText = '☀️ Light Mode';
            }
        }
    </script>
</head>
<body>
    <button id="themeBtn" class="toggle" onclick="toggleTheme()">🌙 Dark Mode</button>
    <h1>QueueCTL Dashboard</h1>
    <div class="stats">
        <div class="stat-box">Total: {{ metrics.total }}</div>
        <div class="stat-box">Completed: {{ metrics.completed }}</div>
        <div class="stat-box">Failed: {{ metrics.failed }}</div>
        <div class="stat-box">Dead: {{ metrics.dead }}</div>
    </div>
    <table>
        <tr>
            <th>ID</th>
            <th>Command</th>
            <th>State</th>
            <th>Attempts</th>
            <th>Priority</th>
            <th>Created</th>
            <th>Updated</th>
        </tr>
        {% for job in jobs %}
        <tr>
            <td>{{ job.id }}</td>
            <td>{{ job.command }}</td>
            <td><span class="badge {{ job.state|lower }}">{{ job.state }}</span></td>
            <td>{{ job.attempts }}</td>
            <td>{{ job.priority }}</td>
            <td>{{ job.created_at }}</td>
            <td>{{ job.updated_at }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

@app.route("/")
def index():
    db = JobDatabase()
    metrics = db.get_metrics()
    jobs = db.list_jobs()
    return render_template_string(TEMPLATE, metrics=metrics, jobs=jobs)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)

