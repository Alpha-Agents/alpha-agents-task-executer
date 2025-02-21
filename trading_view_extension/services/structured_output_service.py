import sys
from pathlib import Path

# Add project root to the Python path so we can import config and other modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel, Field
from openai import OpenAI
# from config import OPENAI_API_KEY
OPENAI_API_KEY = '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' #mikegandia

MODEL = "gpt-4o"

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
                temperature=0.0
            )
            
            trade_signal = completion.choices[0].message.parsed
            
            # Convert TradeSignal instance to JSON
            return trade_signal.model_dump()  # For Pydantic v2

            # Alternative for Pydantic v1
            # return json.dumps(trade_signal.dict())

        except Exception as e:
            print(f"Error extracting trade signal: {e}")
            return None

# Define the schema for structured output, now including an asset field.
# class TradeSignal(BaseModel):
#     asset: str = Field(..., description="The asset or stock symbol, ex: XYZ")
#     action: str = Field(..., description="The trade action: BUY, SELL, WAIT, EXIT (if user is in a trade this is an option)")
#     entry_price: float | None = Field(
#         None, description="The entry price if applicable"
#     )
#     stop_loss: float | None = Field(None, description="Stop loss price if applicable")
#     take_profit: float | None = Field(None, description="Take profit price if applicable")
#     confidence: float | None = Field(None, description="Confidence level from 0 to 10")
#     R2R: float | None = Field(None, description="Risk to reward value")

# class StructuredOutputService:
#     def __init__(self):
#         self.client = OpenAI(api_key=OPENAI_API_KEY)

#     def get_trade_signal(self, user_text: str, asset) -> TradeSignal:
#         """
#         Calls GPT to extract a structured trade signal from user input.
#         The response is expected to include the asset name along with the rest of the fields.
#         """
#         try:
#             completion = self.client.beta.chat.completions.parse(
#                 model=MODEL,
#                 messages=[
#                         {"role": "system", "content": "Extract the trade signal from this message. The response must include the asset name. "},                    
#                         {"role": "user", "content": user_text},
#                 ],
#                 response_format=TradeSignal,
#                 temperature=0.0
#             )
#             return completion.choices[0].message.parsed
#         except Exception as e:
#             print(f"Error extracting trade signal: {e}")
#             return None
        
# if __name__ == "__main__":
#     structured_service = StructuredOutputService()

#     # Example usage: now including an asset name
#     user_input = """Okay, I'm ready. Let's start with the first question.\n\n**1. Market Context & Higher-Timeframe Momentum**\n\nGiven the image shared previously of NVDA on the 1-minute chart, there's a challenge for answering this in full:\n\n*   **No Higher Timeframe:** The image is only a *1-minute* chart. I crucially lack a daily or 4-hour chart to assess the higher-timeframe momentum and answer accurately using the MAs, ADX and/or gaps.\n*   **MAs on Provided Chart:**\n    *   The SMA 50 (orange) is upward sloping on the 1 minute which is bullish.\n    *   The SMA 200 (white) is also beginning to curve upwards which lends support to the bulls longer term.\n*   **Recent Price Action:** There's a clear, strong upward move in the recent price action on the provided chart, with some very minor consolidation before the last candle.\n\nBecause a higher-timeframe view is essential for this question, I cannot confidently evaluate the broader market environment.\n\n**Therefore, due to insufficient data (no daily/4-hour chart), I cannot fully answer this question.** I need the higher-timeframe charts to proceed.\n\nPlease provide the higher timeframe chart as well and I will refine this step of the analysis. Now, let's move to Question 2.\n"""
#     # user_input = """Okay, I have the image and the crops. Let's proceed with step 6.\n\n**6. Based on the identified breakout (or reversal) and the S/R zones, please propose:**\n\n*   **A logical entry point (above/below a pivot or breakout level).**\n*   **A tight stop loss level anchored to a recent swing high/low.**\n*   **A take-profit target at the next major resistance/support or volume cluster.**\n*   **Calculate the potential risk-to-reward (R:R) ratio.**\n\nHere's a potential trade setup based on the current chart:\n\n*   **Entry:** A logical entry point would be just above the recent high, around 6150, anticipating a breakout continuation. There are smaller highs that occurred between the 19th and 20th that could be earlier entries, from 6146 to 6148. The most recent breakout has 6144 as a potential entry.\n*   **Stop Loss:** A tight stop loss could be placed just below the low of the consolidation range, around 6140. This minimizes risk while still giving the trade some room to breathe. Another option could be half that distance, at 6145, which is just below the immediate low of the prior candle.\n*   **Take Profit:** A take-profit target could be set at the next resistance level or at measured move objectives 6178-6200. For this example, around 6180.\n* **Risk-Reward Ratio:**\n    *   Entry: 6145\n        Stop: 6140\n        Target: 6180\n    *   Risk: 6145-6140 = 5\n    *   Reward: 6180-6145 = 35\n        R:R: 35/5= 7 (1:7)\n* **Risk-Reward Ratio 2:**\n    * Entry: 6146\n      Stop: 6140\n      Target: 6176\n       Risk: 6146-6140 = 6\n       Reward: 6176-6146 = 30\n       R:R is 5 (1:5)\n\n**In summary:** The trade offers a good risk-reward ratio if triggered.\n\nLet's proceed to the final question with the given information."""
#     signal = structured_service.get_trade_signal(user_input)

#     if signal:
#         print(signal.dict())
#     else:
#         print("Failed to extract trade signal.")
