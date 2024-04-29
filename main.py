import base64
import logging
import requests
from google.cloud import secretmanager
from twilio.rest import Client

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)  # Capture DEBUG, INFO, WARNING, ERROR, CRITICAL
if not root_logger.handlers:
    # Create console handler and set its log level to DEBUG
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # Create formatter and add it to the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    # Add the handler to the root logger
    root_logger.addHandler(ch)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Capture DEBUG, INFO, WARNING, ERROR, CRITICAL

metadata_server_url = "http://metadata/computeMetadata/v1/project/project-id"
headers = {"Metadata-Flavor": "Google"}
project_id = requests.get(metadata_server_url, headers=headers).text

def fetch_gcp_secret(secret_name: str) -> str:
        # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret.
    secret_version = 'latest'
    name = f"projects/{project_id}/secrets/{secret_name}/versions/{secret_version}"

    # Access the secret version.
    response = client.access_secret_version(request={"name": name})
    secret_string = response.payload.data.decode("UTF-8")
    return secret_string

def send_TWILIO_message(message: str):
    account_sid = fetch_gcp_secret("twilio-acct-sid")
    auth_token = fetch_gcp_secret("twilio-acct-token")
    client = Client(account_sid, auth_token)
    message = client.messages.create(from_=fetch_gcp_secret("twilio-phone-from"), body=message, to=fetch_gcp_secret("twilio-phone-to"))
    logger.debug(f"Message sent: {message.sid}")

def cloud_build_result_notification(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    logger.debug(f"RECEIVED CLOUD BUILD NOTIFICATION: {pubsub_message}")
    if 'status' in pubsub_message:
        if pubsub_message['status'] == 'SUCCESS':
            send_TWILIO_message("Repository build successful".format(pubsub_message['repoName']))
        else:
            send_TWILIO_message("Repository build failed".format(pubsub_message['repoName']))
    logger.debug(f"Decoded Pub/Sub message: {pubsub_message}")

