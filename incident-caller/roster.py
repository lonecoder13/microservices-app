from typing import List, Dict, Any

# Example seed data. Replace with your org data or load from DB.
PROJECTS: Dict[str, Dict[str, Dict[str, Any]]] = {
	"Project1": {
		"Dev": {
			"default": [["+911234567890"], ["+919876543210"], ["+441234567890"]],
			"override": []
		},
		"DevOps": {
			"default": [["+441234567890"], ["+331234567890"]],
			"override": []
		},
		"SRE": {
			"default": [["+331234567890"], ["+351234567890"]],
			"override": []
		},
	},
	"Project2": {
		"Dev": {"default": [["+151234567890"]], "override": []},
		"DevOps": {"default": [["+491234567890"]], "override": []},
		"SRE": {"default": [["+611234567890"]], "override": []},
	},
}


def list_projects() -> List[str]:
	return sorted(PROJECTS.keys())


def list_teams(project: str) -> List[str]:
	return sorted(PROJECTS.get(project, {}).keys())


def get_roster_tiers(project: str, team: str) -> List[List[str]]:
	team_data = PROJECTS.get(project, {}).get(team, None)
	if not team_data:
		return []
	return team_data["override"] if team_data.get("override") else team_data.get("default", [])


def set_override(project: str, team: str, tiers: List[List[str]]):
	if project in PROJECTS and team in PROJECTS[project]:
		PROJECTS[project][team]["override"] = tiers


def reset_override(project: str, team: str):
	if project in PROJECTS and team in PROJECTS[project]:
		PROJECTS[project][team]["override"] = []

