#!/usr/bin/env python3
"""
System Monitor & Alert Script
Monitors CPU, memory, disk usage and sends email alerts when thresholds are exceeded.

"""

import os
import sys
import time
import smtplib
import logging
import argparse

from email.message import EmailMessage
from datetime import datetime
from pathlib import Path

try:
	import psutil
except ImportError:
	print("Error: psutil library is required. Install with: pip install psutil", file=sys.stderr)
	sys.exit(1)

try:
	# Try to load env from .env file if present
	from dotenv import load_dotenv
	load_dotenv() 
except ImportError:
	pass

try:
	import schedule
	SCHEDULE_AVAILABLE = True
except ImportError:
	SCHEDULE_AVAILABLE = False

# --------------------------- CONSTANTS --------------------------- #

# Thresholds (%)
DEFAULT_CPU_THRESHOLD = 80      
DEFAULT_MEMORY_THRESHOLD = 80   
DEFAULT_DISK_THRESHOLD = 90

# Retrieve from .env or use default values
CPU_THRESHOLD = float(os.getenv('CPU_THRESHOLD', DEFAULT_CPU_THRESHOLD))
MEMORY_THRESHOLD = float(os.getenv('MEMORY_THRESHOLD', DEFAULT_MEMORY_THRESHOLD))
DISK_THRESHOLD = float(os.getenv('DISK_THRESHOLD', DEFAULT_DISK_THRESHOLD))

# Email setup
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')

LOG_DIR = Path(os.getenv('LOG_DIR', str(Path.home() / '.system_monitor')))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'monitor.log'

# ---------------------------------------------------------------- #

def setup_logging():
	"""
    Configure and return a logger instance with both file and console handlers.
    File handler uses rotating logs (10 MB max, 5 backups).
    Console handler shows WARNING and above.
	
    """

	# Setup logging Instance
	logger = logging.getLogger('SystemMonitor')
	logger.setLevel(logging.INFO) # remember logging levels in linux fundamental? debug, info, notice, warn, error, critical, alert, emergency

	# Setup handlers

	# File
	from logging.handlers import RotatingFileHandler
	# RotatingFileHandler auto rotates (create new file), when current gets too big
	# max size 10MB
	fh = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
	fh.setLevel(logging.INFO)
	
	# Console
	ch = logging.StreamHandler()
	ch.setLevel(logging.WARNING)

	# formatter
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s') # this formatting is logging specific
	fh.setFormatter(formatter)
	ch.setFormatter(formatter)

	# Add handlers to logger object
	logger.addHandler(fh)
	logger.addHandler(ch)

	return logger

# Initialize logger
logger = setup_logging()

# CPU, Memory, Disk Usage

def get_cpu_usage() -> float:
	"""
	Return current CPU usage percentage.

	interval is delay or sleep before capture.

	"""

	return psutil.cpu_percent(interval=1)

def get_memory_usage() -> float:
	"""
	Return current memory (RAM) usage percentage.

	"""

	return psutil.virtual_memory().percent

def get_disk_usage() -> list[dict]:
	"""
	Return disk usage for all mounted partitions, excluding pseudo filesystems.

	"""
	
	disks = []
	# disk_partitions return partition object (sdiskpart) with 4 attributes
	# mountpoint, device, fstype, opts
	for partition in psutil.disk_partitions():
		# skip pseudo filesystems
		if partition.fstype in ('squashfs', 'tmpfs', 'devtmpfs', 'proc', 'sysfs'):
			continue
		try:
			# also can direct use C:// or D:// which is same .mountpoint
			usage = psutil.disk_usage(partition.mountpoint)
			# all unit default bytes
			disks.append({
				'mountpoint': partition.mountpoint,
                'device': partition.device,
                'total_gb': usage.total / (1024**3),
                'used_gb': usage.used / (1024**3),
                'free_gb': usage.free / (1024**3),
                'percent': usage.percent
			})

		except PermissionError:
			continue
	
	return disks

def get_system_info() -> dict:
	"""
	Collect all system metrics into a dictionary.

	"""

	return {
        'timestamp': datetime.now().isoformat(),
        'cpu_percent': get_cpu_usage(),
        'memory_percent': get_memory_usage(),
        'disks': get_disk_usage()
    }

def check_thresholds(info: dict) -> list[str]:
	"""
    Compare collected system metrics against configured thresholds.
    Return a list of alert messages if any values exceed limits.

    """

	alerts = []
	if info['cpu_percent'] > CPU_THRESHOLD:
		alerts.append(f"CPU usage is high: {info['cpu_percent']:.1f}% (threshold: {CPU_THRESHOLD}%)")

	if info['memory_percent'] > MEMORY_THRESHOLD:
		alerts.append(f"Memory usage is high: {info['memory_percent']:.1f}% (threshold: {MEMORY_THRESHOLD}%)")
	
	for disk in info['disks']:
		if disk['percent'] > DISK_THRESHOLD:
			alerts.append(
				f"Disk {disk['mountpoint']} ({disk['device']}) usage is high: "
				f"{disk['percent']:.1f}% (threshold: {DISK_THRESHOLD}%)"
				)
			
	return alerts

def send_email_alert(subject: str, body: str) -> bool:
	"""
    Send an email alert with the given subject and body using SMTP credentials.
    Return True if successful, False otherwise.

    """

	# Safety Guard
	if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
		logger.error("Email credentials not fully configured. Cannot send alert.")
		return False
	
	message = EmailMessage()
	message.set_content(body)
	message['Subject'] = subject
	message['From'] = SENDER_EMAIL
	message['To'] = RECIPIENT_EMAIL

	try:
		with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
			server.starttls()
			server.login(SENDER_EMAIL, SENDER_PASSWORD)
			server.send_message(message)
		# goes into log file but does not show in console because file handler accepts log INFO level while console handler only WARNING+ Level.
		logger.info(f"Alert email sent: {subject}")

		return True

	except Exception as e:
		logger.error(f"Failed to send email: {e}") 

		return False
	
def run_check(send_alerts: bool = True) -> dict:
	"""
	Perform a single system check, log results, and optionally send alerts.

	"""

	# fetch current system data
	info = get_system_info()

	# log the data
	logger.info(f"CPU: {info['cpu_percent']:.1f}%, Memory: {info['memory_percent']:.1f}%")
	for disk in info['disks']:
		logger.debug(f"Disk {disk['mountpoint']}: {disk['percent']:.1f}% used")
	
	alerts = check_thresholds(info)
	if alerts:
		logger.warning(f"Alerts triggered: {len(alerts)} issue(s)")
		for alert in alerts:
			logger.warning(f"  - {alert}")

		if send_alerts:
			subject = f"System Monitor Alert - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

			body = "The following thresholds were exceeded:\n\n" + "\n".join(alerts)

			body += f"\n\nCPU: {info['cpu_percent']:.1f}%\nMemory: {info['memory_percent']:.1f}%\n"
			body += "Disk usage:\n"

			for disk in info['disks']:
				body += f"  {disk['mountpoint']}: {disk['percent']:.1f}% ({disk['free_gb']:.1f} GB free)\n"
				
			send_email_alert(subject, body)
		
	else:
		logger.info("All metrics within normal ranges.")
	
	return info

def main():
	"""
	Parse command-line arguments and orchestrate monitoring behavior.
    Supports single check (--once), continuous monitoring (--interval),
    or scheduled checks (--schedule). Handles email alert toggling.

	"""

	parser = argparse.ArgumentParser(
		description="System Monitor & Alert Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  # Run a single check
  python system_monitor.py --once

  # Monitor continuously every 60 seconds
  python system_monitor.py --interval 60

  # Schedule checks every 5 minutes (requires schedule library)
  python system_monitor.py --schedule 5

Environment variables:
  CPU_THRESHOLD, MEMORY_THRESHOLD, DISK_THRESHOLD
  SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL
  LOG_DIR
        """
	)

	# mutually exclusive means only one of this arg can be run at a time. Not more than one.
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument('--once', action='store_true', help='Run a single check and exit')
	group.add_argument('--interval', type=int, metavar='SECONDS', help='Run continuously with given interval')
	group.add_argument('--schedule', type=int, metavar='MINUTES', help='Schedule checks every N minutes (requires schedule library)')

	# normal argument
	parser.add_argument('--no-alerts', action='store_true', help='Disable email alerts (useful for testing)')

	args = parser.parse_args()

	# Handle args

	# Safety guard
	if not args.no_alerts and not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
		logger.warning("Email credentials incomplete. Alerts will be logged but not sent.")
		args.no_alerts = True
	
	# handle --once
	if args.once:
		# if args.no_alerts is True, then send_alerts is not True which is False.
		run_check(send_alerts=not args.no_alerts)
		return 0
	
	# handle --interval
	elif args.interval:
		logger.info(f"Starting continuous monitoring every {args.interval} seconds.")

		try:
			while True:
				run_check(send_alerts=not args.no_alerts)
				time.sleep(args.interval)
		except KeyboardInterrupt:
			logger.info("Monitoring stopped by user.")
			return 0
	
	# handle --schedule
	elif args.schedule:
		if not SCHEDULE_AVAILABLE:
			print("Error: 'schedule' library not installed. Install with: pip install schedule", file=sys.stderr)
			return 1

		logger.info(f"Scheduling checks every {args.schedule} minutes.")

		# Define schedule job first
		schedule.every(args.schedule).minutes.do(run_check, send_alerts=not args.no_alerts)

		try:
			while True:
				# Run pending job
				schedule.run_pending()
				time.sleep(1)
		except KeyboardInterrupt:
			logger.info("Scheduled monitoring stopped by user.")
			return 0
	
	return 0

if __name__ == "__main__":
	sys.exit(main())