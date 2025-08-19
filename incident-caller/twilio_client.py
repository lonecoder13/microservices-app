from twilio.rest import Client
from config import Config


def get_twilio_client() -> Client:
	return Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)

