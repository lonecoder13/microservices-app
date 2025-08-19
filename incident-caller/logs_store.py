import sqlite3
from typing import Optional, List
from contextlib import contextmanager
from config import Config


@contextmanager
def _conn():
	con = sqlite3.connect(Config.DB_PATH)
	con.row_factory = sqlite3.Row
	try:
		yield con
		con.commit()
	finally:
		con.close()


def init_db():
	with _conn() as con:
		con.execute(
			"""
			CREATE TABLE IF NOT EXISTS incidents (
				id TEXT PRIMARY KEY,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				triggered_by TEXT,
				project TEXT,
				team TEXT,
				message TEXT,
				priority TEXT,
				call_type TEXT,
				status TEXT  -- OPEN, ACKED, CLOSED
			)
			"""
		)
		con.execute(
			"""
			CREATE TABLE IF NOT EXISTS call_attempts (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				incident_id TEXT,
				attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				tier INTEGER,
				phone TEXT,
				result TEXT,    -- Responded / No Answer / Unreachable / Dialed
				response TEXT
			)
			"""
		)


def create_incident(incident_id: str, triggered_by: str, project: str, team: str,
					message: str, priority: str, call_type: str):
	with _conn() as con:
		con.execute(
			"INSERT INTO incidents(id, triggered_by, project, team, message, priority, call_type, status) VALUES (?,?,?,?,?,?,?,?)",
			(incident_id, triggered_by, project, team, message, priority, call_type, "OPEN"),
		)


def update_incident_status(incident_id: str, status: str):
	with _conn() as con:
		con.execute("UPDATE incidents SET status=? WHERE id=?", (status, incident_id))


def add_call_attempt(incident_id: str, tier: int, phone: str, result: str, response: str = ""):
	with _conn() as con:
		con.execute(
			"INSERT INTO call_attempts(incident_id, tier, phone, result, response) VALUES (?,?,?,?,?)",
			(incident_id, tier, phone, result, response),
		)


def list_logs(filters: Optional[dict] = None) -> List[sqlite3.Row]:
	filters = filters or {}
	query = (
		"SELECT i.created_at as time, i.project, i.team, i.message, i.priority, i.call_type, i.status, "
		"a.tier, a.phone, a.result, a.response, i.id as incident_id "
		"FROM incidents i LEFT JOIN call_attempts a ON i.id = a.incident_id "
	)
	clauses, args = [], []
	if project := filters.get("project"):
		clauses.append("i.project = ?")
		args.append(project)
	if team := filters.get("team"):
		clauses.append("i.team = ?")
		args.append(team)
	if status := filters.get("status"):
		clauses.append("i.status = ?")
		args.append(status)
	if clauses:
		query += " WHERE " + " AND ".join(clauses)
	query += " ORDER BY i.created_at DESC, a.attempted_at ASC"
	with _conn() as con:
		return con.execute(query, args).fetchall()

