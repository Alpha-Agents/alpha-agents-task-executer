import sys
from pathlib import Path

# Add project root to the Python path so we can import config and other modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel, Field
from openai import OpenAI
from config import OPENAI_API_KEY

MODEL = "gpt-4o"

# Define the schema for structured output, now including an asset field.
class TradeSignal(BaseModel):
    asset: str = Field(..., description="The asset or stock symbol, ex: XYZ")
    action: str = Field(..., description="The trade action: BUY, SELL, WAIT, EXIT (if user is in a trade this is an option)")
    entry_price: float | None = Field(
        None, description="The entry price if applicable"
    )
    stop_loss: float | None = Field(None, description="Stop loss price if applicable")
    take_profit: float | None = Field(None, description="Take profit price if applicable")
    confidence: float | None = Field(None, description="Confidence level from 0 to 10")
    R2R: float | None = Field(None, description="Risk to reward value")

class StructuredOutputService:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def get_trade_signal(self, user_text: str) -> TradeSignal:
        """
        Calls GPT to extract a structured trade signal from user input.
        The response is expected to include the asset name along with the rest of the fields.
        """
        try:
            completion = self.client.beta.chat.completions.parse(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "Extract the trade signal from this message. The response must include the asset name."},
                    {"role": "user", "content": user_text},
                ],
                response_format=TradeSignal,
                temperature=0.0
            )
            return completion.choices[0].message.parsed
        except Exception as e:
            print(f"Error extracting trade signal: {e}")
            return None

# if __name__ == "__main__":
#     structured_service = StructuredOutputService()

#     # Example usage: now including an asset name
#     user_input = "Buy META at 350 with a stop loss at 345 and a target at 365. The asset is META."
#     signal = structured_service.get_trade_signal(user_input)

#     if signal:
#         print(signal.dict())
#     else:
#         print("Failed to extract trade signal.")
