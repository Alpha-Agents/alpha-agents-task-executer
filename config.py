import os
import logging
from dotenv import load_dotenv
import boto3
from dataclasses import dataclass
from pathlib import Path
from botocore.config import Config

# Load environment variables from the .env file
load_dotenv()

# --------------------------
# General Configuration
# --------------------------
PORT = int(os.getenv("PORT", 8000))
DATABASE_URL = os.getenv("DATABASE_URL")

# --------------------------
# Logging Configuration
# --------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOG_FILE = os.getenv("LOG_FILE", "trading_view_extension.log")

# Configure logging for the application
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),  # Log to file
        logging.StreamHandler(),        # Log to console
    ],
)
logger = logging.getLogger(__name__)

# --------------------------
# WebSocket host and port
# --------------------------
WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "localhost")
WEBSOCKET_PORT = int(os.getenv("PORT", 8080))

# --------------------------
# Directory for uploaded files
# --------------------------
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# --------------------------
# AWS Configuration
# --------------------------
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


PROJECT_ROOT = Path(__file__).parent / "trading_view_extension" 

DEBUG_PORT = "9223"

sqs_client = boto3.client(
    'sqs',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
    config=Config(connect_timeout=10, read_timeout=15) 
)

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# --------------------------
# Data Classes for AWS SQS Queues
# --------------------------
@dataclass
class SQSQueue:
    name: str
    url: str
    arn: str
    client: boto3.client

# Initialize separate SQSQueue objects
input_tasks_queue = SQSQueue(
    name=os.getenv("SQS_INPUT_QUEUE_NAME"),
    url=os.getenv("SQS_INPUT_QUEUE_URL"),
    arn=os.getenv("SQS_INPUT_QUEUE_ARN"),
    client=sqs_client
)

output_tasks_queue = SQSQueue(
    name=os.getenv("SQS_OUTPUT_QUEUE_NAME"),
    url=os.getenv("SQS_OUTPUT_QUEUE_URL"),
    arn=os.getenv("SQS_OUTPUT_QUEUE_ARN"),
    client=sqs_client
)

# --------------------------
# AWS S3 Configuration
# --------------------------
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# # --------------------------
# # AWS RDS Configuration
# # --------------------------
DATABASE_URL = "postgresql://postgres:2012@localhost:5432/postgres"

SMALL_STEP = False

CONFIDENCE_THRESHOLD = 7
R2R_THRESHOLD = 2.5

MAX_TRADES = 150

DEFAULT_PROMPT = """Your role is to analyze stock charts with exceptional expertise. You will provide your analysis, your expert opinion on if you should BUY / SELL / WAIT.
                    You will provide a confidence score of your decision (1-100%). And you will provide entry, profit target, and stop loss, for any BUY or SELL decision. 
                    You will also calculate the R:R (risk to reward ratio) when applicable.
                    Note: The price will be highlighed on the right side as the same color as the indicator Respond in markdown format."""
DEFAULT_QUERY = "Do you see any trade setups? How confident are you? Trade or wait?"
