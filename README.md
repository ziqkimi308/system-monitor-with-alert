# 🖥️ System Monitor & Alert Script

A Python script that monitors CPU, memory, and disk usage — and sends email alerts when configurable thresholds are exceeded. Supports single checks, continuous polling, and scheduled runs via cron or the `schedule` library.

---

## Features

- Real-time CPU, memory, and disk usage monitoring via `psutil`
- Email alerts via `smtplib` with TLS (Gmail-compatible)
- Rotating log files to track historical events
- Environment variable configuration with optional `.env` support
- Three run modes: one-shot, continuous interval, or scheduled
- Graceful shutdown on `Ctrl+C`

---

## Requirements

- Python 3.10+
- Required packages:

```bash
pip install psutil python-dotenv schedule
```

> **Gmail users:** You'll need an [App Password](https://myaccount.google.com/apppasswords) if 2FA is enabled.

---

## Usage

```bash
# Run a single check (no email)
python system_monitor.py --once --no-alerts

# Monitor continuously every 30 seconds
python system_monitor.py --interval 30

# Schedule checks every 5 minutes
python system_monitor.py --schedule 5
```

Sample Output:
```bash
2026-05-31 08:13:44,240 - SystemMonitor - INFO - CPU: 22.5%, Memory: 35.5%
2026-05-31 08:13:44,240 - SystemMonitor - INFO - All metrics within normal ranges.
```

```bash
2026-05-31 08:17:05,027 - SystemMonitor - INFO - Starting continuous monitoring every 30 seconds.
2026-05-31 08:17:06,033 - SystemMonitor - INFO - CPU: 7.0%, Memory: 35.4%
2026-05-31 08:17:06,033 - SystemMonitor - INFO - All metrics within normal ranges.
2026-05-31 08:17:37,036 - SystemMonitor - INFO - CPU: 11.5%, Memory: 35.3%
2026-05-31 08:17:37,036 - SystemMonitor - INFO - All metrics within normal ranges.
```

### Arguments

| Flag | Description |
|------|-------------|
| `--once` | Run a single check and exit |
| `--interval SECONDS` | Run continuously at the given interval |
| `--schedule MINUTES` | Schedule checks every N minutes (requires `schedule`) |
| `--no-alerts` | Disable email alerts (useful for testing) |

---

## Configuration

Create a `.env` file in the project directory:

```env
# Thresholds
CPU_THRESHOLD=80
MEMORY_THRESHOLD=85
DISK_THRESHOLD=90

# Email (Gmail example)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
RECIPIENT_EMAIL=alerts@example.com

# Optional: custom log directory
LOG_DIR=/var/log/system_monitor
```

All values can also be passed as system environment variables. Add `.env` to `.gitignore` — never commit credentials.

---

## Logs

Logs are written to `~/.system_monitor/monitor.log` by default (configurable via `LOG_DIR`).  
The log rotates automatically at 10 MB and keeps up to 5 backups.

---

## Cron Setup (Linux/macOS)

Run every 10 minutes via crontab (`crontab -e`):
```
*/10 * * * * /usr/bin/python3 /path/to/system_monitor.py --once >> /var/log/monitor_cron.log 2>&1
```

---

## Tech Stack

| Library | Purpose |
|---------|---------|
| `psutil` | System metrics (CPU, memory, disk) |
| `smtplib` | Email alerts over TLS |
| `logging` + `RotatingFileHandler` | Persistent rotating logs |
| `python-dotenv` | `.env` file support |
| `schedule` | Periodic task scheduling |
| `argparse` | CLI interface |
