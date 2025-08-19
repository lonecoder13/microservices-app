import os
from dotenv import load_dotenv

load_dotenv()


class Config:
	SECRET_KEY = os.getenv("SECRET_KEY", "changeme-secret")

	# Twilio
	TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
	TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
	TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

	# Public base URL for Twilio webhooks (set via ngrok in dev)
	PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:5000")

	# SQLite DB
	DB_PATH = os.getenv("DB_PATH", "incident_caller.db")

	# Call flow
	AUTO_ACK_TIMEOUT_SEC = int(os.getenv("AUTO_ACK_TIMEOUT_SEC", "25"))  # gather timeout
	BETWEEN_TIER_WAIT_SEC = int(os.getenv("BETWEEN_TIER_WAIT_SEC", "10"))

