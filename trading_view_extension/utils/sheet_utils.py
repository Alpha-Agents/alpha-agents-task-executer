import sys
from pathlib import Path
import re

# Add project root to the Python path so we can import config and other modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import SERVICE_ACCOUNT_PATH, SPREADSHEET_ID, ALL_ASSISTANTS_START_RANGE, SELECTED_ASSISTANTS_RANGE, TAKE_IMAGE_RANGE, SEPARATED_RANGE, NUMBER_OF_IMAGES_RANGE, USER_PROMPT_RANGE, OUTPUT_START_RANGE

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

def get_selected_assistants_ids_prompts():
    full_range = get_full_range(SPREADSHEET_ID, ALL_ASSISTANTS_START_RANGE)
    all_assistants_data = read_data(SPREADSHEET_ID, full_range)

    # Read the selected assistants range
    selected_assistants_titles = read_data(SPREADSHEET_ID, SELECTED_ASSISTANTS_RANGE)

    # Ensure we have a proper list of assistant titles (flatten & split by commas)
    selected_assistants_list = []
    for titles_group in selected_assistants_titles:
        if titles_group:  # Ensure it's not an empty row
            selected_assistants_list.extend([title.strip() for title in titles_group[0].split(',')])

    # Find corresponding assistant IDs and prompts
    assistant_ids = find_assistants_ids(selected_assistants_list, all_assistants_data)
    assistant_prompts = find_assistants_prompts(selected_assistants_list, all_assistants_data)

    # Return as proper lists
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

def get_user_prompt():
    """
    Reads the USER_PROMPT_RANGE from the spreadsheet and returns the user prompt as a string.

    Returns:
        str: The user prompt if available, otherwise an empty string.
    """
    # Read data from the specified range
    user_prompt_data = read_data(SPREADSHEET_ID, USER_PROMPT_RANGE)

    # Check if data exists and extract the first value, or return an empty string if empty
    if user_prompt_data and user_prompt_data[0]:
        return user_prompt_data[0][0]  # Extract the string from [["user prompt here"]]
    else:
        return "follow prompt"

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

def write_structured_signal(spreadsheet_id, assistant_title: str, signal, column_offset: int):
    """
    Writes the structured output to the sheet starting at the given OUTPUT_START_RANGE,
    shifting each structured response to the right (one column per assistant).

    Example layout for column_offset=0 (starts at B13):
        B13: Assistant Title
        B14: action
        B15: current_price
        B16: stop_loss
        B17: take_profit
        B18: confidence
        B19: R2R

    On the next assistant (column_offset=1, moves to C13):
        C13: Assistant Title
        C14: action
        C15: current_price
        C16: stop_loss
        C17: take_profit
        C18: confidence
        C19: R2R
    """

    # Extract the starting sheet, column, and row
    OUTPUT_SHEET_NAME, OUTPUT_START_COL, OUTPUT_START_ROW = extract_start_position(OUTPUT_START_RANGE)

    # Build an ordered list of (label, value) pairs
    fields = [
        ("Assistant Title", assistant_title),
        ("Action", signal.action),
        ("Current Price", signal.current_price),
        ("Stop Loss", signal.stop_loss),
        ("Take Profit", signal.take_profit),
        ("Confidence", signal.confidence),
        ("R2R", signal.R2R)
    ]

    for row_offset, (label, value) in enumerate(fields):
        # Compute the correct cell address
        col_num = OUTPUT_START_COL + column_offset  # Move one column over per structured output
        row_num = OUTPUT_START_ROW + row_offset  # Move row-by-row for the fields
        col_letter = col_to_letter(col_num)
        cell_range = f"{OUTPUT_SHEET_NAME}!{col_letter}{row_num}"

        # Write to Google Sheet
        write_data(
            spreadsheet_id,
            cell_range,
            [[value if value is not None else ""]]  # Handle None values gracefully
        )

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

def clear_output_range():
    """
    Clears the values from the full range determined by output_start_range.

    Args:
        spreadsheet_id (str): The ID of the Google Spreadsheet.
        output_start_range (str): The starting range (e.g., 'CONSOLE!B13').

    Returns:
        None
    """


    try:
        # Get the full range of data to clear
        full_range = get_full_range(SPREADSHEET_ID, OUTPUT_START_RANGE)

        # Read the existing data to determine how many rows and columns need to be cleared
        existing_data = read_data(SPREADSHEET_ID, full_range)

        if not existing_data:
            print(f"No data to clear in {full_range}.")
            return

        # Create a blank structure to overwrite the existing data
        empty_values = [[""] * len(existing_data[0]) for _ in range(len(existing_data))]

        # Write empty values to clear the range
        write_data(SPREADSHEET_ID, full_range, empty_values)

        print(f"Cleared data in range: {full_range}")

    except Exception as e:
        print(f"Error clearing output range: {e}")



def main():


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

    user_prompt = get_user_prompt()
    print(user_prompt)

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

if __name__ == "__main__":
    main()