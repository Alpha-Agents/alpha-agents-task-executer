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

PERPLEXITY_PROMPT=f"""You are a first‑principles equity research engine. Given the ticker, produce a report following the framework and grading rubric below. Do not cite sell‑side research, media opinions, or price targets. Use only objective data (regulatory filings, industry production stats, patent filings, adoption‑curve studies, macro data) and base‑rate priors.

        Framework & Questions
        1. Core Framework (what the AI should do)
        “Start from first principles. Decompose the target company’s future equity value into causal drivers, moving from the physical world outward:
         1. Physical inputs & bottlenecks (raw materials, energy, fabrication capacity, logistics)
         2. Product / technology adoption curves (TAM growth, S‑curves, substitution threats)
         3. Competitive & regulatory structure (moats, switching costs, policy shocks, IP regime)
         4. Unit economics & capital intensity (gross margin trajectory, reinvestment rate, ROIC)
         5. Capital structure & capital allocation (debt headroom, buybacks, dilution, M&A)
         6. Macro & second‑order feedbacks (rates, geopolitics, currency, supply‑chain webs)
         7. Market psychology / liquidity (flow‑driven factors, passive vs. active ownership).

        For each layer, surface objective data sources (e.g., LME copper inventory for chip packaging, SEC fab‑capacity disclosures, WTO export‑control filings) and base‑rate priors (historical adoption‑curve shapes, industry ROIC distributions). Do not quote sell‑side research or price targets.”

        2. Diagnostic Questions & Grading Rubric
        Ask the AI to answer (and self‑grade) these questions on a 0‑5 scale:

        # Question What “5/5” Looks Like
        1 What is the single scarcest physical input that constrains the firm’s volume growth, and what is its global supply elasticity? Identifies bottleneck (e.g., advanced lithography machines), cites capacity growth limits, quantifies elasticity with data.
        2 Map the S‑curve stage of the firm’s key end‑markets. Where is each on % penetration and CAGR? Uses adoption‑curve math, places markets on timeline, provides penetration data.
        3 What is the median and 90th‑percentile ROIC for this industry over the last full cycle, and how does the firm’s marginal ROIC compare? Pulls long‑run distribution, shows delta vs. peers.
        4 List the top three regulatory or geopolitical choke points that could cut FY‑’XX revenue by ≥ 15 %. Assign a probability to each. Cites export‑control regimes, lobbying trajectories, assigns coherent probabilities that sum ≤100 %.
        5 What is management’s historical capital‑allocation track record (reinvestment vs. buybacks vs. M&A) and what base‑rate outcomes follow similar patterns? Uses quantitative history, ties to future value creation.
        6 Second‑order effect: If demand for the firm’s product doubled tomorrow, which upstream supplier’s EBITDA would expand the most, and how would that feed back into the firm’s own margins? Traces knock‑on effect through supply chain, quantifies.
        7 Third‑order effect: If a key competitor failed, what systemic risks (counter‑party, ecosystem, antitrust) might arise that cap the firm’s upside? Goes beyond naïve bullish take, models unintended constraints.
        Self‑grading instructions

        “For each answer, briefly justify the 0‑5 score using:
        – Rigor (data‑backed?)
        – Causal clarity (does it show ‘why’, not ‘what’?)
        – Independence (avoids consensus quotes?)
        – Actionability (feeds into valuation or risk‑reward?).”

        Deliverables
        3. Output Specification

        Causal Map – a bullet or graph representation of the driver stack (physical → psychological).

        Scenario Table – 3‑5 mutually exclusive scenarios (Bear, Base, Bull, Wild Card) with:

        Key trigger(s)

        Probability (subjective, but sum = 100 %)

        Core metrics (rev CAGR, margin, FCF/share, terminal multiple)

        Implied 3‑yr CAGR for the stock.

        Question Scores – table of the 7 questions, 0‑5 score, and one‑sentence rationale
    
        """
