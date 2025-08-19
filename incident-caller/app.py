from flask import Flask, render_template, request, redirect, url_for, jsonify
from config import Config
from logs_store import init_db, list_logs
from roster import list_projects, list_teams, get_roster_tiers
from call_flow import new_incident, start_automated_escalation, start_manual_escalation, handle_acknowledge
from twilio.twiml.voice_response import VoiceResponse, Gather

app = Flask(__name__)
app.config.from_object(Config)
init_db()


@app.route("/")
def index():
	projects = list_projects()
	default_project = projects[0] if projects else ""
	teams = list_teams(default_project) if default_project else []
	return render_template("dashboard.html", projects=projects, teams=teams)


@app.route("/teams")
def teams():
	project = request.args.get("project", "")
	return jsonify({"teams": list_teams(project)})


@app.route("/trigger", methods=["POST"])
def trigger():
	project = request.form.get("project", "")
	team = request.form.get("team", "")
	message = request.form.get("message", "")
	priority = request.form.get("priority", "P2")
	call_type = request.form.get("call_type", "AUTOMATED")
	triggered_by = request.form.get("triggered_by", "web")
	incident_id = new_incident(triggered_by, project, team, message, priority, call_type)
	if call_type.upper() == "AUTOMATED":
		start_automated_escalation(incident_id)
	else:
		start_manual_escalation(incident_id)
	return redirect(url_for("logs"))


@app.route("/logs")
def logs():
	filters = {k: request.args.get(k) for k in ["project", "team", "status"] if request.args.get(k)}
	rows = list_logs(filters)
	return render_template("logs.html", rows=rows)


# Twilio webhooks for AUTOMATED flow
@app.route("/twiml/incident/<incident_id>", methods=["POST", "GET"])
def twiml_incident(incident_id: str):
	tier = int(request.args.get("tier", "1"))
	phone = request.args.get("phone", "")
	vr = VoiceResponse()
	gather = Gather(num_digits=1, action=url_for("twiml_ack", incident_id=incident_id, tier=tier, phone=phone, _external=True), timeout=Config.AUTO_ACK_TIMEOUT_SEC)
	gather.say(f"Incident for team. Message: {request.args.get('message', 'Please acknowledge')}. Press 1 to acknowledge.")
	vr.append(gather)
	vr.say("No input received. Goodbye.")
	return str(vr)


@app.route("/twiml/incident/<incident_id>/ack", methods=["POST"])
def twiml_ack(incident_id: str):
	tier = int(request.args.get("tier", "1"))
	phone = request.args.get("phone", "")
	digit = request.form.get("Digits", "")
	vr = VoiceResponse()
	if digit == "1":
		handle_acknowledge(incident_id, tier, phone)
		vr.say("Acknowledged. Thank you.")
	else:
		vr.say("Input not recognized. Goodbye.")
	return str(vr)


# Twilio webhooks for MANUAL flow
@app.route("/twiml/manual/start/<incident_id>", methods=["POST", "GET"])
def twiml_manual_start(incident_id: str):
	tier = int(request.args.get("tier", "1"))
	# Build dynamic menu for the tier's phone numbers
	from roster import get_roster_tiers
	numbers = []
	# In a real system we would fetch state; to keep it simple, ask for index 1..N and then redirect
	vr = VoiceResponse()
	gather = Gather(num_digits=1, action=url_for("twiml_manual_select", incident_id=incident_id, tier=tier, _external=True))
	gather.say(f"Manual escalation tier {tier}. Press 1 to call first contact, 2 for second, 3 for third.")
	vr.append(gather)
	vr.say("No input received. Goodbye.")
	return str(vr)


@app.route("/twiml/manual/select/<incident_id>", methods=["POST"]) 
def twiml_manual_select(incident_id: str):
	from roster import get_roster_tiers
	tier = int(request.args.get("tier", "1"))
	digit = request.form.get("Digits", "")
	vr = VoiceResponse()
	# Map digit to phone in that tier
	# We assume 1..N maps to the list order
	s = call_state(incident_id)
	tiers = get_roster_tiers(s["project"], s["team"]) if s else []
	numbers = tiers[tier - 1] if 0 < tier <= len(tiers) else []
	try:
		idx = int(digit) - 1
		phone = numbers[idx]
	except Exception:
		phone = ""
	if phone:
		# Bridge call: dial the selected number
		vr.say(f"Dialing selected contact.")
		dial = vr.dial(caller_id=Config.TWILIO_FROM_NUMBER)
		dial.number(phone, url=url_for("twiml_manual_after_dial", incident_id=incident_id, tier=tier, phone=phone, _external=True))
	else:
		vr.say("Invalid selection. Goodbye.")
	return str(vr)


@app.route("/twiml/manual/after/<incident_id>", methods=["POST", "GET"]) 
def twiml_manual_after_dial(incident_id: str):
	tier = int(request.args.get("tier", "1"))
	phone = request.args.get("phone", "")
	vr = VoiceResponse()
	# Ask callee to press 1 to acknowledge
	gather = Gather(num_digits=1, action=url_for("twiml_ack", incident_id=incident_id, tier=tier, phone=phone, _external=True), timeout=Config.AUTO_ACK_TIMEOUT_SEC)
	gather.say("Please press 1 to acknowledge the incident.")
	vr.append(gather)
	vr.say("No input received. Goodbye.")
	return str(vr)


def call_state(incident_id: str):
	from call_flow import STATE
	return STATE.get(incident_id)


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5000, debug=True)