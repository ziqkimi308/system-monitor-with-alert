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

def get_disk_usage() -> float:
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
	"""

	alerts = []
	if info['cpu_percent'] > CPU_THRESHOLD:
		alerts.append(f"CPU usage is high: {info['cpu_percent']:.1f}% (threshold: {CPU_THRESHOLD}%)")

	if info['memory_percent'] > MEMORY_THRESHOLD:
		alerts.append(f"Memory usage is high: {info['memory_percent']:.1f}% (threshold: {MEMORY_THRESHOLD}%)")
	
	for disk in info['disks']:
		if disk['percent'] > DISK_THRESHOLD:
			alerts.append(alerts.append(
				f"Disk {disk['mountpoint']} ({disk['device']}) usage is high: "
				f"{disk['percent']:.1f}% (threshold: {DISK_THRESHOLD}%)"
				))
			
	return alerts

def send_email_alert(subject: str, body: str) -> bool:
	"""
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