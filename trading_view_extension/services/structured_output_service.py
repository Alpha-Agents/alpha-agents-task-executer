import sys
from pathlib import Path

# Add project root to the Python path so we can import config and other modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel, Field
from openai import OpenAI
# from config import OPENAI_API_KEY
OPENAI_API_KEY = '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' #mikegandia

MODEL = "o3-mini"

class TradeSignal(BaseModel):
    asset: str = Field(..., description="The asset or stock symbol, ex: XYZ")
    action: str = Field(..., description="The trade action: BUY, SELL, WAIT, EXIT (if user is in a trade this is an option)")
    entry_price: float | None = Field(None, description="The entry price if applicable")
    stop_loss: float | None = Field(None, description="Stop loss price if applicable")
    take_profit: float | None = Field(None, description="Take profit price if applicable")
    confidence: float | None = Field(None, description="Confidence level from 0 to 10")
    R2R: float | None = Field(None, description="Risk to reward value")

class StructuredOutputService:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def get_trade_signal(self, user_text: str, asset: str) -> str:
        """
        Calls GPT to extract a structured trade signal from user input and returns it in JSON format.
        """
        try:
            completion = self.client.beta.chat.completions.parse(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "Extract the trade signal from this message. The response must include the asset name."},                    
                    {"role": "user", "content": user_text},
                ],
                response_format=TradeSignal,
            )
            
            trade_signal = completion.choices[0].message.parsed
            
            # Convert TradeSignal instance to JSON
            return trade_signal.model_dump()  # For Pydantic v2

            # Alternative for Pydantic v1
            # return json.dumps(trade_signal.dict())

        except Exception as e:
            print(f"Error extracting trade signal: {e}")
            return None