import sys
from pathlib import Path

# Add the project root (where config.py is located) to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9223 --incognito --user-data-dir=/tmp/chrome_debug

import os
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from typing import Optional
from config import CHROME_DRIVER_PATH, SCREENSHOTS_FOLDER, DEBUG_PORT


def take_screenshot(
    chrome_driver_path: str = CHROME_DRIVER_PATH,
    screenshots_folder: str = SCREENSHOTS_FOLDER,
    debug_port: str = DEBUG_PORT
) -> Optional[str]:
    """
    Take a screenshot using Chrome in debug mode.
    Saves the screenshot in the specified folder with a timestamped filename.

    Args:
        chrome_driver_path (str): Path to the ChromeDriver executable.
        screenshots_folder (str): Folder where the screenshots will be saved.
        debug_port (str): Port for Chrome in debug mode.

    Returns:
        Optional[str]: Path to the saved screenshot or None if an error occurred.
    """
    # Configure Chrome options
    options = Options()
    options.debugger_address = f"127.0.0.1:{debug_port}"

    try:
        # Start WebDriver
        service = Service(chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=options)

        # Ensure screenshots folder exists
        os.makedirs(screenshots_folder, exist_ok=True)

        # Generate timestamped file path
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = os.path.join(screenshots_folder, f"tradingview_chart_{timestamp}.png")

        # Capture and save the screenshot
        driver.save_screenshot(screenshot_path)
        # print(f"Screenshot saved: {screenshot_path}")

        return screenshot_path

    except Exception as e:
        print(f"Screenshot error: {e}")
        return None

    finally:
        driver.quit()


def get_latest_screenshot(folder_path: str = SCREENSHOTS_FOLDER) -> Optional[str]:
    """
    Get the most recent screenshot based on the timestamp in the filename.

    Args:
        folder_path (str): Path to the folder containing screenshots.

    Returns:
        Optional[str]: Path to the most recent screenshot or None if no screenshots are found.
    """

    # print(f"folder_path: {folder_path}")
    # print(f"Absolute path: {os.path.abspath(folder_path)}")

    # print("Contents of folder_path:", os.listdir(folder_path))

    try:
        # List files that match the screenshot naming convention
        files = [
            f for f in os.listdir(folder_path)
            if f.startswith("tradingview_chart_") and f.endswith(".png")
        ]
        if not files:
            print("No screenshots found.")
            return None

        # Sort files by timestamp extracted from the filename
        files.sort(key=lambda x: os.path.getmtime(os.path.join(folder_path, x)), reverse=True)
        latest_file = files[0]
        latest_file_path = os.path.join(folder_path, latest_file)
        print(f"Latest screenshot: {latest_file_path}")
        return latest_file_path

    except Exception as e:
        print(f"Error getting the latest screenshot: {e}")
        return None


# Main entry point
if __name__ == "__main__":
    # Take a screenshot
    screenshot_path = take_screenshot()
    if screenshot_path:
        print(f"New screenshot saved: {screenshot_path}")
    
    # Get the latest screenshot
    latest_screenshot = get_latest_screenshot()
    if latest_screenshot:
        print("Success")
    else:
        print("No screenshots found.")# Main entry point