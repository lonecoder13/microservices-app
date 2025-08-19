import time
import uuid
from typing import List, Dict
from threading import Thread, Lock
from flask import url_for
from urllib.parse import quote_plus

from config import Config
from roster import get_roster_tiers
from twilio_client import get_twilio_client
from logs_store import create_incident, update_incident_status, add_call_attempt

# In-memory incident state (simple for MVP)
STATE: Dict[str, Dict] = {}
STATE_LOCK = Lock()


def new_incident(triggered_by: str, project: str, team: str, message: str, priority: str, call_type: str) -> str:
	incident_id = str(uuid.uuid4())
	with STATE_LOCK:
		STATE[incident_id] = {
			"ack": False,
			"current_tier": 0,
			"mode": call_type,  # AUTOMATED or MANUAL
			"project": project,
			"team": team,
			"message": message,
			"priority": priority,
			"waiting_operator": False,
		}
	create_incident(incident_id, triggered_by, project, team, message, priority, call_type)
	return incident_id


def start_automated_escalation(incident_id: str):
	Thread(target=_run_automated, args=(incident_id,), daemon=True).start()


def start_manual_escalation(incident_id: str):
	Thread(target=_run_manual, args=(incident_id,), daemon=True).start()


def _twiml_url(path: str) -> str:
	# Build absolute URL for Twilio to call back
	base = Config.PUBLIC_BASE_URL.rstrip('/')
	return f"{base}{path}"


def _run_automated(incident_id: str):
	client = get_twilio_client()
	s = STATE[incident_id]
	tiers = get_roster_tiers(s["project"], s["team"]) or []
	for tier_index, numbers in enumerate(tiers, start=1):
		if s["ack"]:
			break
		# Call all numbers in the tier in parallel (or sequential; here parallel simplified as quick loop)
		for phone in numbers:
			try:
				client.calls.create(
					to=phone,
					from_=Config.TWILIO_FROM_NUMBER,
					url=_twiml_url(
						f"/twiml/incident/{incident_id}?tier={tier_index}&phone={phone}&message={quote_plus(s.get('message',''))}"
					),
				)
				add_call_attempt(incident_id, tier_index, phone, result="Dialed", response="")
			except Exception as e:
				add_call_attempt(incident_id, tier_index, phone, result="Unreachable", response=str(e))
		# Wait between tiers if not acknowledged
		waited = 0
		while waited < Config.BETWEEN_TIER_WAIT_SEC and not STATE[incident_id]["ack"]:
			time.sleep(1)
			waited += 1
		if STATE[incident_id]["ack"]:
			break
	# Finalize
	update_incident_status(incident_id, "ACKED" if STATE[incident_id]["ack"] else "CLOSED")


def _run_manual(incident_id: str):
	client = get_twilio_client()
	s = STATE[incident_id]
	tiers = get_roster_tiers(s["project"], s["team"]) or []
	for tier_index, numbers in enumerate(tiers, start=1):
		if s["ack"]:
			break
		# Place a single call to operator to select a target in this tier
		s["waiting_operator"] = True
		try:
			client.calls.create(
				to=Config.TWILIO_FROM_NUMBER,
				from_=Config.TWILIO_FROM_NUMBER,
				url=_twiml_url(f"/twiml/manual/start/{incident_id}?tier={tier_index}"),
			)
		except Exception as e:
			# If operator call fails, skip to next tier after wait
			add_call_attempt(incident_id, tier_index, "operator", result="Unreachable", response=str(e))
		# Wait between tiers for ack
		waited = 0
		while waited < Config.BETWEEN_TIER_WAIT_SEC and not STATE[incident_id]["ack"]:
			time.sleep(1)
			waited += 1
		if STATE[incident_id]["ack"]:
			break
	# Finalize
	update_incident_status(incident_id, "ACKED" if STATE[incident_id]["ack"] else "CLOSED")


def handle_acknowledge(incident_id: str, tier: int, phone: str):
	with STATE_LOCK:
		if incident_id in STATE:
			STATE[incident_id]["ack"] = True
			STATE[incident_id]["current_tier"] = tier
	add_call_attempt(incident_id, tier, phone, result="Responded", response="ACK")
	update_incident_status(incident_id, "ACKED")