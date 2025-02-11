import sys
from pathlib import Path
import json
import re
# Add project root to the Python path so we can import config and other modules
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from pydantic import BaseModel, Field
from openai import OpenAI
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


from config import MODEL, API_KEY, logger
client = OpenAI(api_key=API_KEY)

# Define the schema for structured output
class TradeSignal(BaseModel):
    asset: str = Field(..., description="The asset or stock name letters/ticker: XYZ")
    action: str = Field(..., description="The trade action: BUY, SELL, or WAIT")
    current_price: float | None = Field(None, description="The current price which will also be the entry or exit price if applicable")
    stop_loss: float | None = Field(None, description="Stop loss price if applicable")
    take_profit: float | None = Field(None, description="Take profit price if applicable")
    confidence: float | None = Field(None, description="Confidence level from 0 to 10")
    R2R: float | None = Field(None, description="Risk to reward value")

class StructuredOutputService:
    def __init__(self, client: OpenAI):
        self.client = client

    # def get_trade_signal(self, user_text: str) -> TradeSignal:
    #     """
    #     Calls GPT to extract a structured trade signal from user input.
    #     """
    #     try:
    #         completion = self.client.beta.chat.completions.parse(
    #             model=MODEL,
    #             messages=[
    #                 {"role": "system", "content": "Extract the trade signal from this message."},
    #                 {"role": "user", "content": user_text},
    #             ],
    #             response_format=TradeSignal,
    #             temperature=0.0
    #         )
    #         return completion.choices[0].message.parsed
    #     except Exception as e:
    #         print(f"Error extracting trade signal: {e}")
    #         return None
    # import json


    def get_trade_signal(self, user_text: str) -> TradeSignal:
        """
        Calls GPT to extract a structured trade signal from user input.
        """
        try:
            completion = self.client.chat.completions.create(
                model=MODEL,
                messages=[
                        {"role": "system", "content": """Extract the trade signal from this message.
                        **YOU MUST RETURN ONLY JSON. DO NOT RETURN ANY TEXT, EXPLANATION, OR MARKDOWN.** 
                        The response **MUST** be a valid JSON object with this exact format:

                        ```json
                        {
                            "asset"": "stock name",  
                            "action": "BUY",  // or "SELL" or "WAIT"
                            "current_price": Current price,
                            "stop_loss": Stop Loss price,
                            "take_profit": Price at which profit should be booked,
                            "confidence": confidence between 1 to 10,
                            "R2R": Risk to Reward Ratio (1.5, 2.5)

                        }"""
                       },
                       {"role": "user", "content": user_text},
                ],
                temperature=0.0
            )

            raw_response = completion.choices[0].message.content.strip()

            if raw_response.startswith("```json"):
                raw_response = re.sub(r"```json\n|\n```", "", raw_response).strip()

            try:
                parsed_response = json.loads(raw_response)  # Convert AI output to dict
                trade_signal = TradeSignal(**parsed_response)  # Convert dict to Pydantic model
                return trade_signal

            except json.JSONDecodeError:
                logger.error(f"ERROR: AI response is not valid JSON: {raw_response}")
                return {"error": "AI returned invalid JSON"}

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": str(e)}



# if __name__ == "__main__":
#     structured_service = StructuredOutputService(client)

#     # Example usage
#     user_input = "Buy META at 350 with a stop loss at 345 and a target at 365."
    
#     signal = structured_service.get_trade_signal(user_input)

#     if signal:
#         print(signal)
#     else:
#         print("Failed to extract trade signal.")
