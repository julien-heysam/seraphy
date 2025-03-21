import cv2
import numpy as np
import pyautogui
import json
import time
from typing import Tuple, Dict, List, Any
import easyocr # More accurate than pytesseract for this use case
from backend.infrastructure.enhanced_browser import SeleniumEnhancedBrowser
from difflib import SequenceMatcher
import openai
import base64
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from backend import API_KEYS


class VisionAutomationAgent:
    def __init__(self):
        self.browser = SeleniumEnhancedBrowser()
        # Initialize OCR reader once (supports multiple languages if needed)
        self.element_mapping = {}  # Store mapping between element IDs and elements
        
    def execute_action(self, action: Dict):
        """Execute a single recorded action"""
        action_type = action['type']
        # breakpoint()
        api_key = API_KEYS.OPENAI_API_KEY
        if action_type == 'navigate':
            self.browser.navigate_to(action['url'])
            time.sleep(2)  # Wait for page load
            # The browser.navigate_to already calls highlight_elements
            # Just need to create our mapping
            self.highlight_clickable_elements()
        
        elif action_type == 'click_text':
            try:
                # First try to find element by text in our mapping
                try:
                    element_info = self.get_element_by_text(action['field_name'])
                    
                    # If we have an element ID, use the more reliable click_element_by_number method
                    if 'element_id' in element_info:
                        self.click_element_by_number(int(element_info['element_id']))
                    else:
                        self.click_at_position(element_info['x'], element_info['y'])
                except Exception as e:
                    print(f"Element mapping click failed: {str(e)}")
                    # If element not found in mapping, use the vision API as fallback
                    # Take a screenshot with highlighted elements
                    screenshot = self.capture_browser_screenshot()
                    screenshot_path = "screenshot_with_highlights.png"
                    cv2.imwrite(screenshot_path, screenshot)
                    
                    # Use OpenAI to find the number associated with the text
                    try:
                        number = find_text_position_with_openai(screenshot_path, action['field_name'], api_key)
                        if number:
                            self.click_element_by_number(number)
                        else:
                            raise Exception(f"Could not find element with field_name '{action['field_name']}'")
                    except Exception as e:
                        raise Exception(f"OpenAI vision failed: {str(e)}")

                if 'wait_after' in action:
                    time.sleep(action['wait_after'])
                    
            except Exception as e:
                print(f"Failed to find and click text '{action['field_name']}': {str(e)}")
                
        elif action_type == 'click_element_number':
            # New action type to click by element number
            try:
                self.click_element_by_number(action['number'])
                if 'wait_after' in action:
                    time.sleep(action['wait_after'])
            except Exception as e:
                print(f"Failed to click element number {action['number']}: {str(e)}")
                
        elif action_type == 'input':
            # First try to find input field by its label in our mapping
            try:
                element_info = self.get_element_by_text(action['field_name'])
                # If we have an element ID, use the more reliable click_element_by_number method
                if 'element_id' in element_info:
                    self.click_element_by_number(int(element_info['element_id']))
                else:
                    self.click_at_position(element_info['x'], element_info['y'])
            except Exception:
                screenshot = self.capture_browser_screenshot()
                screenshot_path = "screenshot_with_highlights.png"
                cv2.imwrite(screenshot_path, screenshot)
                # Fallback to original method
                number = find_text_position_with_openai(screenshot_path, action['field_name'], api_key)
                if number and number != 'idk':
                    self.click_element_by_number(number)
                else:
                    raise Exception(f"Could not find element with text '{action['field_name']}'")
                
            # Type the text
            pyautogui.write(action['value'], interval=0.1)
            
        elif action_type == 'wait':
            time.sleep(action['duration'])
        

    def run_task(self, recording_path: str):
        """Execute a task based on recorded actions"""
        try:
            # with open(recording_path, 'r') as f:
            #     steps = json.load(f)
            steps = [
                {
                    "type": "navigate",
                    "url": "https://heysam.ai"
                },
                {
                    "type": "click_text",
                    "field_name": "Login",
                    "description": "Click login button",
                    "wait_after": 2
                },
                {
                    "type": "click_text",
                    "field_name": "answerquestions",
                    "description": "Click answer questions button to access Bulk Q&A",
                    "wait_after": 1
                },
                {
                    "type": "input",
                    "field_name": "Email",
                    "value": "user@example.com",
                    "description": "Enter email"
                }
            ]
            
            # Highlight clickable elements before starting
            
            # Save the initial mapping to a file for analysis
            
            for step in steps:
                self.highlight_clickable_elements()
                self.save_element_mapping_to_file()
                self.execute_action(step)
                
        except Exception as e:
            print(f"Error executing task: {str(e)}")
        finally:
            self.browser.cleanup()



def find_text_position_with_openai(image_path: str, target_text: str, api_key: str) -> Tuple[int, int]:
    """
    Finds the position of text in an image using the OpenAI Vision API.

    Args:
        image_path: Path to the image file.
        target_text: The text to search for.
        api_key: Your OpenAI API key.

    Returns:
        A tuple (x, y) representing the center coordinates of the text, or raises an exception if not found.
    """

    # Function to encode the image
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    base64_image = encode_image(image_path)

    client = openai.OpenAI(api_key=api_key)

    # The prompt can be tuned to get better results
    prompt = f"Find the element with the text '{target_text}'. All clickable elements are numbered and highlighted with colored borders. Return ONLY the NUMBER of the element associated with this text. If you can't find it, respond with 'idk'."
    breakpoint()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            }
        ],
        max_tokens=1000,
    )
    
    # Check for errors – the openai package generally handles this, but we'll add some checks
    if not response.choices:
        raise Exception("OpenAI API returned no choices.")

    try:
        # Extract coordinates from the response (this is highly dependent on the actual response format)
        return response.choices[0].message.content

    except (KeyError, ValueError) as e:
        raise Exception(f"Failed to parse OpenAI API response: {e} - Full response: {response.choices[0].message.content}") from e


if __name__ == "__main__":
    agent = VisionAutomationAgent()
    agent.run_task("recordings/recording_20250317_144242_text.json")
