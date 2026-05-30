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
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	fh.setFormatter(formatter)
	ch.setFormatter(formatter)

	# Add handlers to logger object
	logger.addHandler(fh)
	logger.addHandler(ch)

	return logger

# Initialize logger
logger = setup_logging()

