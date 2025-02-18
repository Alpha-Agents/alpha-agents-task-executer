import sys
from pathlib import Path
import re

import pandas as pd


# Add project root to the Python path so we can import config and other modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import (
    SERVICE_ACCOUNT_PATH, SPREADSHEET_ID, ALL_ASSISTANTS_START_RANGE, 
    SELECTED_ASSISTANTS_RANGE, TAKE_IMAGE_RANGE, SEPARATED_RANGE, NUMBER_OF_IMAGES_RANGE, 
    USER_PROMPT_RANGE, OUTPUT_START_RANGE, MULTI_OUTPUT_START_RANGE, AUTO_TIME_FRAME_RANGE,
    AUTO_POSITION_RANGE, AUTO_STOP_LOSS_RANGE, AUTO_TAKE_PROFIT_RANGE, COT_QUESTIONS_START_RANGE, 
    MULTI_RESULT_START_RANGE
)

# Load credentials
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH, scopes=SCOPES)
sheets_service = build('sheets', 'v4', credentials=credentials)

def read_data(spreadsheet_id, range_str):
    """Read data from a specific range in the Google Sheet."""
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_str
    ).execute()
    return result.get('values', [])

def write_data(spreadsheet_id, range_str, values):
    """Write data to a specific range in the Google Sheet."""
    body = {"values": values}
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_str,
        valueInputOption="RAW",
        body=body
    ).execute()

def get_assistants_ids_prompts(assistant_range: str):
    """
    Retrieves assistant IDs, prompts, and a list of selected assistant titles
    from a given range in the Google Sheet.

    Args:
        assistant_range (str): The cell range in the Google Sheet that contains
                               the selected assistant titles. (For example, "Sheet1!A2:A5")

    Returns:
        tuple: A tuple containing three lists:
            - assistant_ids: The list of assistant IDs corresponding to the selected assistants.
            - assistant_prompts: The list of prompts corresponding to the selected assistants.
            - selected_assistants_list: The list of assistant titles (as strings).
    """
    # Get the full assistants data from the master range (constant defined in your config)
    full_range = get_full_range(SPREADSHEET_ID, ALL_ASSISTANTS_START_RANGE)
    all_assistants_data = read_data(SPREADSHEET_ID, full_range)

    # Read the selected assistants from the provided range.
    selected_assistants_titles = read_data(SPREADSHEET_ID, assistant_range)

    # Ensure we have a proper list of assistant titles by flattening and splitting by commas.
    selected_assistants_list = []
    for titles_group in selected_assistants_titles:
        if titles_group:  # Ensure it's not an empty row.
            # Assume the titles are in the first column of each row.
            selected_assistants_list.extend([title.strip() for title in titles_group[0].split(',')])

    # Find corresponding assistant IDs and prompts using your helper functions.
    assistant_ids = find_assistants_ids(selected_assistants_list, all_assistants_data)
    assistant_prompts = find_assistants_prompts(selected_assistants_list, all_assistants_data)

    return assistant_ids, assistant_prompts, selected_assistants_list

def get_is_take_image():
    """
    Reads the TAKE_IMAGE_RANGE from the spreadsheet and returns a boolean value.

    Returns:
        bool: True if the value is 'TRUE', False otherwise.
    """
    is_take_image = read_data(SPREADSHEET_ID, TAKE_IMAGE_RANGE)

    # Check if data exists and extract the first value
    if is_take_image and is_take_image[0]:  # Ensure there is data and it's not empty
        return is_take_image[0][0].strip().upper() == 'TRUE'

    # Default to False if the value is not found or invalid
    return False

def get_number_of_images():
    """
    Reads the NUMBER_OF_IMAGES range from the spreadsheet and returns the number of images.

    Returns:
        int: The number of images specified in the spreadsheet.
    """
    # Read the NUMBER_OF_IMAGES range from the spreadsheet
    number_of_images_data = read_data(SPREADSHEET_ID, NUMBER_OF_IMAGES_RANGE)

    # Check if data exists and extract the number
    if number_of_images_data and number_of_images_data[0]:  # Ensure there is data and it's not empty
        try:
            # Convert the first value to an integer
            return int(number_of_images_data[0][0])
        except ValueError:
            print("Error: NUMBER_OF_IMAGES value is not a valid integer.")
            return 0  # Default to 0 if conversion fails

    # Default to 0 if the value is not found
    return 0

def get_user_prompt(prompt_range: str):
    """
    Reads the USER_PROMPT_RANGE from the spreadsheet and returns the user prompt as a string.

    Returns:
        str: The user prompt if available, otherwise an empty string.
    """
    # Read data from the specified range
    user_prompt_data = read_data(SPREADSHEET_ID, prompt_range)

    # Check if data exists and extract the first value, or return an empty string if empty
    if user_prompt_data and user_prompt_data[0]:
        return user_prompt_data[0][0]  # Extract the string from [["user prompt here"]]
    else:
        return ""

def get_time_frame(time_frame_range: str) -> list:
    """
    Reads the specified time frame range from the spreadsheet and returns a list of human-readable
    time frame strings in a fixed order.
    
    For example:
      - If the cell contains "1M, 10M, D, 1Hour", it returns ["1 day", "1 hour", "10 minutes", "1 minute"].
    
    Args:
        time_frame_range (str): The cell range in the Google Sheet that contains the time frame value.
        
    Returns:
        list: A list of formatted time frame strings, sorted in the order: day, hour, 10 minutes, 1 minute.
    """
    # Read data from the specified range.
    time_frame_data = read_data(SPREADSHEET_ID, time_frame_range)
    
    # Extract the raw value.
    if time_frame_data and time_frame_data[0]:
        raw_value = time_frame_data[0][0].strip()
    else:
        raw_value = ""
    
    # Mapping dictionary (normalized keys in lower-case)
    mapping = {
        "d": "1 day",
        "1h": "1 hour",
        "10m": "10 minutes",
        "1m": "1 minute"
    }
    # Define a desired order for the tokens (using normalized keys).
    order_priority = {
        "d": 0,
        "1h": 1,
        "10m": 2,
        "1m": 3
    }
    
    # Split raw value by commas, strip whitespace, and normalize to lower-case.
    tokens = [token.strip().lower() for token in raw_value.split(',') if token.strip()]
    
    # Sort tokens according to the desired order. Tokens not in order_priority get a high index.
    sorted_tokens = sorted(tokens, key=lambda t: order_priority.get(t, 99))
    
    # Map each token to its human-readable value, defaulting to the token itself if not found.
    return [mapping.get(token, token) for token in sorted_tokens]

def get_is_separated():
    """
    Reads a cell from the Google Sheet, e.g. 'TRUE' or 'FALSE',
    returns True/False. Make sure your sheet has that cell.
    """
    data = read_data(SPREADSHEET_ID, SEPARATED_RANGE)  # e.g. 'Console!D2'
    if data and data[0]:
        return data[0][0].strip().upper() == 'TRUE'
    return False

def find_assistants_ids(requested_titles, assistants_data):
    """
    Match requested assistant titles with their corresponding IDs.

    Args:
        requested_titles (list of str): List of assistant titles to match.
        assistants_data (list of list): Data read from the "Assistants" tab.

    Returns:
        list of str: List of assistant IDs matching the requested titles.
    """
    title_to_id = {row[1]: row[0] for row in assistants_data if len(row) >= 2}

    requested_ids = []
    for title in requested_titles:  # No need for titles_group[0], already split earlier
        stripped_title = title.strip()
        if stripped_title in title_to_id:
            requested_ids.append(title_to_id[stripped_title])
    return requested_ids

def find_assistants_prompts(requested_titles, assistants_data):
    """
    Match requested assistant titles with their corresponding prompts.

    Args:
        requested_titles (list of str): List of assistant titles to match.
        assistants_data (list of list): Data read from the "Assistants" sheet
            where row structure is [assistant_id, title, prompt].

    Returns:
        list of str: List of prompts matching the requested titles.
    """
    title_to_prompt = {row[1]: row[2] for row in assistants_data if len(row) >= 3}

    requested_prompts = []
    for title in requested_titles:  # No need for titles_group[0]
        stripped_title = title.strip()
        if stripped_title in title_to_prompt:
            requested_prompts.append(title_to_prompt[stripped_title])
    return requested_prompts

def get_full_range(spreadsheet_id, start_range):
    """
    Determine the full range of non-empty rows and columns starting from the specified range.

    Args:
        spreadsheet_id (str): The ID of the Google Spreadsheet.
        start_range (str): The starting range (e.g., 'AVATARS!A3').

    Returns:
        str: The full range of the non-empty data (e.g., 'AVATARS!A3:B10').

    Raises:
        ValueError: If no data is found starting from the range.
    """
    try:
        # Extract the sheet name and starting cell
        sheet_name, start_cell = start_range.split('!')
        start_row = int(''.join(filter(str.isdigit, start_cell)))
        start_col_letter = ''.join(filter(str.isalpha, start_cell))

        # Read all data from the sheet
        all_data = read_data(spreadsheet_id, sheet_name)

        if not all_data or len(all_data) < start_row - 1:
            raise ValueError(f"No data found starting from range: {start_range}")

        # Determine the first and last rows and columns of filled data
        filled_data = all_data[start_row - 1:]  # Offset rows to start from A3
        end_row = start_row + len(filled_data) - 1
        end_col = max(len(row) for row in filled_data)

        # Convert the column index back to letters
        def col_to_letter(col):
            result = ""
            while col > 0:
                col, remainder = divmod(col - 1, 26)
                result = chr(65 + remainder) + result
            return result

        end_col_letter = col_to_letter(end_col)
        full_range = f"{sheet_name}!{start_col_letter}{start_row}:{end_col_letter}{end_row}"
        return full_range
    except Exception as e:
        raise RuntimeError(f"Failed to determine full range: {e}")

def col_to_letter(col: int) -> str:
    """
    Convert a 1-based column index to a spreadsheet column letter (A, B, C, ...).
    For example: 1 -> "A", 2 -> "B", 27 -> "AA".
    """
    result = ""
    while col > 0:
        col, remainder = divmod(col - 1, 26)
        result = chr(65 + remainder) + result
    return result

def extract_start_position(output_range: str):
    """
    Extracts the starting column (as a number) and row (as an integer)
    from a range string like 'CONSOLE!B13'.
    
    Returns:
        sheet_name (str): The sheet name (e.g., 'CONSOLE')
        start_col (int): The starting column index (1-based, e.g., B -> 2)
        start_row (int): The starting row number (e.g., 13)
    """
    match = re.match(r"(.+?)!([A-Z]+)(\d+)", output_range)
    if not match:
        raise ValueError(f"Invalid output range format: {output_range}")

    sheet_name, start_col_letter, start_row = match.groups()
    
    # Convert column letter to a number
    start_col = sum((ord(c) - 64) * (26 ** i) for i, c in enumerate(reversed(start_col_letter)))
    
    return sheet_name, start_col, int(start_row)

def write_structured_signal(output_start_range, assistant_title: str, signal, row_offset: int, column_offset: int = 0):
    """
    Writes the structured output in a transposed layout so that each assistant's output is on one row.
    For example, if output_start_range is 'CONSOLE!B13' and row_offset is 0, then:
    
        B13: Assistant Title
        C13: Action
        D13: Current Price
        E13: Stop Loss
        F13: Take Profit
        G13: Confidence
        H13: R2R

    Instead of updating cell by cell, this version updates the entire row at once.

    Args:
        output_start_range (str): The starting range (e.g., 'CONSOLE!B13').
        assistant_title (str): The title of the assistant.
        signal: The structured signal containing the fields.
        row_offset (int): The relative row offset (0-based) from the starting cell.
        column_offset (int): The number of columns to offset horizontally (default is 0).
    """
    # Extract the starting sheet, column, and row from the given range.
    OUTPUT_SHEET_NAME, OUTPUT_START_COL, OUTPUT_START_ROW = extract_start_position(output_start_range)

    # Prepare the row of values, ensuring that None values are replaced with an empty string.
    fields = [
        assistant_title,
        signal.action,
        signal.current_price,
        signal.stop_loss,
        signal.take_profit,
        signal.confidence,
        signal.R2R
    ]
    row_values = [value if value is not None else "" for value in fields]

    # Calculate the starting row and columns
    row_num = OUTPUT_START_ROW + row_offset
    start_col_num = OUTPUT_START_COL + column_offset
    end_col_num = start_col_num + len(row_values) - 1

    # Convert column numbers to letters.
    start_col_letter = col_to_letter(start_col_num)
    end_col_letter = col_to_letter(end_col_num)

    # Create a range covering the entire row.
    cell_range = f"{OUTPUT_SHEET_NAME}!{start_col_letter}{row_num}:{end_col_letter}{row_num}"

    # Write the entire row in one update.
    write_data(SPREADSHEET_ID, cell_range, [row_values])

def write_structured_signal_multi_row(row_data, row_index):
    """
    Writes a single row of multi-run results to a separate sheet in one API call.
    
    Args:
        row_data (list): A list of cell values to write in that row.
                         For example, a header row like ["ASSET", "Assistant1", "Assistant2", ...]
                         or a data row like [asset_name, action1, action2, ...].
        row_index (int): The relative row number (0-based) from the starting row.
                         For instance, 0 will write on the starting row, 1 on the next, etc.
    
    This function uses MULTI_OUTPUT_START_RANGE from the config to determine the
    output sheet name, starting column, and starting row.
    """
    # Extract sheet details from the configuration.
    sheet_name, start_col, start_row = extract_start_position(MULTI_OUTPUT_START_RANGE)
    
    # The actual row on the sheet is the starting row plus the relative index.
    actual_row = start_row + row_index

    # Calculate the starting and ending column letters for the row.
    start_letter = col_to_letter(start_col)
    end_letter = col_to_letter(start_col + len(row_data) - 1)
    
    # Define the range covering the entire row.
    cell_range = f"{sheet_name}!{start_letter}{actual_row}:{end_letter}{actual_row}"
    
    # Replace any None values with empty strings.
    row_values = [value if value is not None else "" for value in row_data]
    
    # Write the entire row in one API call.
    write_data(SPREADSHEET_ID, cell_range, [row_values])

def set_trade_info(position, stop_loss, take_profit):
    """
    Writes trade information to the Google Sheet.
    
    Args:
        position: A value (or string) representing the trade position (e.g. "Entered Trade at 350").
        stop_loss: The stop loss value.
        take_profit: The take profit value.
        
    The function writes:
      - The position to the range specified by AUTO_POSITION_RANGE.
      - The stop loss to the range specified by AUTO_STOP_LOSS_RANGE.
      - The take profit to the range specified by AUTO_TAKE_PROFIT_RANGE.
    """
    # Write the position to the designated range.
    write_data(SPREADSHEET_ID, AUTO_POSITION_RANGE, [[position]])
    # Write the stop loss.
    write_data(SPREADSHEET_ID, AUTO_STOP_LOSS_RANGE, [[stop_loss]])
    # Write the take profit.
    write_data(SPREADSHEET_ID, AUTO_TAKE_PROFIT_RANGE, [[take_profit]])
    
def get_trade_info():
    """
    Reads trade information from the Google Sheet and returns it as a dictionary.

    Returns:
        dict: A dictionary with keys:
            - "position": The trade position (e.g. "Entered Trade at 350")
            - "stop_loss": The stop loss value
            - "take_profit": The take profit value
    """
    # Read data from the designated ranges.
    position_data = read_data(SPREADSHEET_ID, AUTO_POSITION_RANGE)
    stop_loss_data = read_data(SPREADSHEET_ID, AUTO_STOP_LOSS_RANGE)
    take_profit_data = read_data(SPREADSHEET_ID, AUTO_TAKE_PROFIT_RANGE)

    # Extract the first cell from each if available.
    position = position_data[0][0] if position_data and position_data[0] else None
    stop_loss = stop_loss_data[0][0] if stop_loss_data and stop_loss_data[0] else None
    take_profit = take_profit_data[0][0] if take_profit_data and take_profit_data[0] else None

    return {
        "position": position,
        "stop_loss": stop_loss,
        "take_profit": take_profit
    }

def test_structured_output():
    """
    Creates three fake trade signals and writes them to the Google Sheet for testing.
    """
    from pydantic import BaseModel

    class TradeSignal(BaseModel):
        action: str
        current_price: float
        stop_loss: float
        take_profit: float
        confidence: float
        R2R: float

    # Simulated trade signals
    signals = [
        TradeSignal(action="BUY", current_price=250.5, stop_loss=245.0, take_profit=270.0, confidence=8.5, R2R=3.0),
        TradeSignal(action="SELL", current_price=180.2, stop_loss=185.0, take_profit=170.0, confidence=7.0, R2R=2.5),
        TradeSignal(action="HOLD", current_price=315.8, stop_loss=310.0, take_profit=330.0, confidence=6.5, R2R=2.0)
    ]

    assistant_titles = ["Backtesting Agent", "Scanner Expert", "Weinstein Trader"]

    # Write each signal to Google Sheet
    for i, signal in enumerate(signals):
        print(f"Writing structured output for: {assistant_titles[i]}")
        print(signal.dict())  # Print for verification before writing

        write_structured_signal(SPREADSHEET_ID, assistant_titles[i], signal, column_offset=i)

    print("Test completed: Structured outputs written to Google Sheet.")

def clear_output_range(output_start_range: str) -> None:
    """
    Clears the values from the full range determined by the given output_start_range.

    Args:
        spreadsheet_id (str): The ID of the Google Spreadsheet.
        output_start_range (str): The starting range (e.g., 'CONSOLE!B13' or 'MULTI_OUTPUT!B13').

    Returns:
        None
    """
    try:
        # Get the full range of data to clear
        full_range = get_full_range(SPREADSHEET_ID, output_start_range)

        # Read the existing data to determine how many rows and columns need to be cleared
        existing_data = read_data(SPREADSHEET_ID, full_range)

        if not existing_data:
            print(f"No data to clear in {full_range}.")
            return

        # Create a blank structure with the same dimensions as the existing data
        empty_values = [[""] * len(existing_data[0]) for _ in range(len(existing_data))]

        # Write the blank structure to clear the range
        write_data(SPREADSHEET_ID, full_range, empty_values)

        print(f"Cleared data in range: {full_range}")

    except Exception as e:
        print(f"Error clearing output range: {e}")

def get_cot_questions(cot_questions_start_range):
    """
    Retrieves a list of CoT questions from the given range in the spreadsheet.
    
    Args:
        cot_questions_start_range (str): The cell range in the Google Sheet (e.g., "CoT!B2:B8")
        
    Returns:
        list: A list of question strings, one for each non-empty cell in the range.
    """
    # Retrieve the full range data (assumes get_full_range returns a list of lists)
    full_range = get_full_range(SPREADSHEET_ID, cot_questions_start_range)
    data = read_data(SPREADSHEET_ID, full_range)
    questions = [cell.strip() for row in data for cell in row if cell and cell.strip()]
    return questions

def get_agent_analysis():
    full_range = get_full_range(SPREADSHEET_ID, MULTI_OUTPUT_START_RANGE)
    data = read_data(SPREADSHEET_ID, full_range)
    
    # If the data appears transposed (more columns than rows), transpose it.
    if len(data) < len(data[0]):
        print("Data appears transposed. Transposing it now...")
        data = list(map(list, zip(*data)))
    
    expected_header = ["SYMBOL", "ACTION", "ENTRY", "STOP LOSS", "TAKE PROFIT", "CONFIDENCE", "R2R"]
    
    # Ensure every row in the data has exactly len(expected_header) columns.
    for i, row in enumerate(data):
        if len(row) != len(expected_header):
            print(f"Warning: Row {i} has {len(row)} columns; expected {len(expected_header)}. Adjusting row.")
            if len(row) > len(expected_header):
                data[i] = row[:len(expected_header)]
            else:
                # Pad with None if there are missing columns.
                data[i] = row + [None] * (len(expected_header) - len(row))
    
    df = pd.DataFrame(data, columns=expected_header)
    return df

def write_agent_results(symbol, result, row_offset):
    """
    Writes the symbol and result to the sheet using the dynamic MULTI_RESULT_START_RANGE.
    It writes the symbol in the base column and the result in the adjacent column.
    The target row is computed by adding row_offset to the base row extracted from MULTI_RESULT_START_RANGE.
    
    For example, if:
        MULTI_RESULT_START_RANGE = "MULTI-RUN!H2"
        row_offset = 3
    then the symbol is written to "MULTI-RUN!H5" and the result to "MULTI-RUN!I5".
    
    This function assumes that write_data(SPREADSHEET_ID, target_range, data) is available.
    """
    
    # Split the range into sheet name and cell reference.
    if "!" in MULTI_RESULT_START_RANGE:
        sheet_name, cell_ref = MULTI_RESULT_START_RANGE.split("!")
    else:
        sheet_name = ""
        cell_ref = MULTI_RESULT_START_RANGE

    def get_next_column(col):
        """
        Given a column letter (e.g., "H"), returns the next column letter (e.g., "I").
        Supports multi-letter columns (e.g., "Z" -> "AA").
        """
        num = 0
        for c in col:
            num = num * 26 + (ord(c) - ord('A') + 1)
        num += 1
        result_col = ""
        while num:
            num, remainder = divmod(num - 1, 26)
            result_col = chr(65 + remainder) + result_col
        return result_col

    # Extract base column and row from the cell reference.
    m = re.match(r"([A-Z]+)(\d+)", cell_ref)
    if not m:
        raise ValueError("Invalid cell reference in MULTI_RESULT_START_RANGE: " + MULTI_RESULT_START_RANGE)
    base_col = m.group(1)
    base_row = int(m.group(2))
    
    # Compute the target row using the row offset.
    target_row = base_row + row_offset
    
    # Build the cell references for symbol and result.
    symbol_cell = f"{base_col}{target_row}"
    result_cell = f"{get_next_column(base_col)}{target_row}"
    
    # Build the target range.
    target_range = f"{symbol_cell}:{result_cell}"
    if sheet_name:
        target_range = f"{sheet_name}!{target_range}"
    
    data_to_write = [[symbol, result]]
    
    # Write the data to the computed range.
    write_data(SPREADSHEET_ID, target_range, data_to_write)


def main():

    # df = get_agent_analysis()
    # print(df)

    symbol = "NFLX"
    result = "TARGET"
    row_offset = 0
    write_agent_results(symbol, result, row_offset)

    # get_cot_questions(COT_QUESTIONS_START_RANGE)

    # set_trade_info("LONG", 345, 365)
    # trade_info = get_trade_info()
    # print(trade_info)
    # # clear_output_range()
    # test_structured_output()

    # assistant_ids, assistant_prompts, assistant_titles = get_selected_assistants_ids_prompts()
    # print(assistant_ids)
    # print(assistant_prompts)
    # print(assistant_titles)

    # is_take_image = get_is_take_image()
    # print(is_take_image)

    # is_separated = get_is_separated()
    # print(is_separated)

    # num_images = get_number_of_images()
    # print(num_images)

    # time_frame = get_time_frame(AUTO_TIME_FRAME_RANGE)
    # print(time_frame)
    # user_prompt = get_user_prompt()
    # print(user_prompt)

    # # Define the range for testing
    # test_read_range = "Console!A1:A5"  # Adjust range based on your sheet
    # test_write_range = "Console!B1:B5"  # Adjust range based on your sheet

    # # Write test data
    # test_values = [["Hello"], ["World"], ["This"], ["Is"], ["Test"]]
    # print("Writing data...")
    # write_data(spreadsheet_id, test_write_range, test_values)
    # print(f"Data written to range {test_write_range}")

    #     # Read back data
    # print("Reading data...")
    # read_values = read_data(spreadsheet_id, test_read_range)
    # print(f"Data read from range {test_read_range}: {read_values}")

# if __name__ == "__main__":
#     main()
