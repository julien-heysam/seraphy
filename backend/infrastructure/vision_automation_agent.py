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
        self.reader = easyocr.Reader(['en'])
        self.element_mapping = {}  # Store mapping between element IDs and elements
        
    def get_browser_coordinates(self) -> Tuple[int, int, int, int]:
        """Get the current browser window position and dimensions"""
        window_rect = self.browser.driver.get_window_rect()
        return (
            window_rect['x'],
            window_rect['y'],
            window_rect['width'],
            window_rect['height']
        )
    
    def capture_browser_screenshot(self) -> np.ndarray:
        """Capture current browser window state"""
        x, y, width, height = self.get_browser_coordinates()
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def find_text_position(self, target_text: str, threshold: float = 0.85, similarity_threshold: float = 0.8) -> Tuple[int, int]:
        """Find the position of text in the current browser window"""
        screenshot = self.capture_browser_screenshot()
        
        # Get all text regions in the image
        results = self.reader.readtext(screenshot)
        
        best_match = None
        best_score = 0
        
        for (bbox, text, score) in results:
            # Normalize texts for comparison
            text = text.lower().strip()
            target = target_text.lower().strip()
            
            similarity = self.text_similarity(text, target)
            if similarity > similarity_threshold and score > threshold:
                if score > best_score:
                    best_match = bbox
                    best_score = score
        
        if best_match is None:
            raise Exception(f"Could not find text '{target_text}' on screen")
        
        # Calculate center point of the bounding box
        # bbox format is: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
        center_x = int((best_match[0][0] + best_match[2][0]) / 2)
        center_y = int((best_match[0][1] + best_match[2][1]) / 2)
        
        return center_x, center_y

    def click_at_position(self, x: int, y: int):
        """Click at specific coordinates relative to browser window"""
        try:
            # First try to use Selenium's built-in actions for more reliable clicking
            # This works with elements that are within the viewport
            actions = ActionChains(self.browser.driver)
            actions.move_by_offset(x, y).click().perform()
            # Reset actions to avoid compounding offsets in future calls
            actions.reset_actions()
            time.sleep(0.5)  # Wait for any animations/changes
        except Exception as e:
            # Fall back to pyautogui if Selenium actions fail
            print(f"Selenium click failed, falling back to pyautogui: {str(e)}")
            browser_x, browser_y, _, _ = self.get_browser_coordinates()
            # Convert coordinates relative to browser window to absolute screen coordinates
            abs_x = browser_x + x
            abs_y = browser_y + y
            
            # Save current mouse position to restore after click
            original_x, original_y = pyautogui.position()
            
            # Smooth move to position (more human-like)
            pyautogui.moveTo(abs_x, abs_y, duration=0.5)
            time.sleep(0.1)  # Small pause before click
            pyautogui.click(abs_x, abs_y)
            time.sleep(0.5)  # Wait for any animations/changes
            
            # Return cursor to original position if it's not where we clicked
            # This helps prevent interference with manual development
            if original_x != abs_x or original_y != abs_y:
                pyautogui.moveTo(original_x, original_y, duration=0.3)
                
    def type_text(self, text: str):
        """Type text at current cursor position"""
        pyautogui.write(text, interval=0.1)  # Add small delay between keystrokes
        
    def highlight_clickable_elements(self) -> Dict[str, Any]:
        """
        Uses the browser's built-in highlight_elements method and builds
        a mapping of element IDs to their details for automation.
        """
        # Use the existing highlight_elements method from SeleniumEnhancedBrowser
        num_elements = self.browser.highlight_elements()
        
        # Now we need to get the mapping of elements to their positions
        mapping_script = """
        const elementMap = {};
        document.querySelectorAll('[data-highlight-id]').forEach(el => {
            const index = el.getAttribute('data-highlight-id');
            const rect = el.getBoundingClientRect();
            
            elementMap[parseInt(index) + 1] = {
                tag: el.tagName,
                text: el.textContent.trim().substring(0, 50), // Limit text length
                x: Math.round(rect.left + rect.width/2),  // center x
                y: Math.round(rect.top + rect.height/2),  // center y
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                href: el.href || null,
                id: el.id || null,
                className: el.className || null
            };
        });
        
        return elementMap;
        """
        
        # Execute the mapping script to get the details of highlighted elements
        element_map = self.browser.driver.execute_script(mapping_script)
        self.element_mapping = element_map
        return element_map
    
    def click_element_by_number(self, element_number: int):
        """Click an element by its numbered identifier"""
        if not self.element_mapping:
            self.highlight_clickable_elements()
            
        if str(element_number) not in self.element_mapping:
            raise Exception(f"Element number {element_number} not found in mapping")
        
        element_info = self.element_mapping[str(element_number)]
        
        # Try to find and click the element directly with JavaScript for more reliability
        js_click = """
        const elements = document.querySelectorAll('[data-highlight-id]');
        for (const el of elements) {
            if (el.getAttribute('data-highlight-id') === arguments[0]) {
                // Scroll element into view if needed
                el.scrollIntoView({behavior: 'smooth', block: 'center'});
                
                // Use a small delay to ensure the element is in view
                setTimeout(() => {
                    // Simulate a more natural click with mouse events
                    const rect = el.getBoundingClientRect();
                    const centerX = rect.left + rect.width/2;
                    const centerY = rect.top + rect.height/2;
                    
                    // Create and dispatch mouse events
                    const mouseDown = new MouseEvent('mousedown', {
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        clientX: centerX,
                        clientY: centerY
                    });
                    
                    const mouseUp = new MouseEvent('mouseup', {
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        clientX: centerX,
                        clientY: centerY
                    });
                    
                    const click = new MouseEvent('click', {
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        clientX: centerX,
                        clientY: centerY
                    });
                    
                    el.dispatchEvent(mouseDown);
                    el.dispatchEvent(mouseUp);
                    el.dispatchEvent(click);
                }, 500);
                
                return true;
            }
        }
        return false;
        """
        
        try:
            clicked = self.browser.driver.execute_script(js_click, str(int(element_number) - 1))
            if clicked:
                time.sleep(1)  # Wait for any animations/changes after JavaScript click
                return
        except Exception as e:
            print(f"JavaScript click failed: {str(e)}")
        
        # If JavaScript click fails, fall back to coordinate-based click
        self.click_at_position(element_info['x'], element_info['y'])
        
    def get_element_by_text(self, target_text: str) -> Dict[str, Any]:
        """Find an element in the mapping by matching its text"""
        if not self.element_mapping:
            self.highlight_clickable_elements()
            
        best_match = None
        best_score = 0
        best_id = None
        
        for element_id, element_info in self.element_mapping.items():
            element_text = element_info['text']
            similarity = self.text_similarity(element_text, target_text)
            
            if similarity > 0.8 and similarity > best_score:
                best_match = element_info
                best_score = similarity
                best_id = element_id
                
        if not best_match:
            raise Exception(f"Could not find element with text '{target_text}'")
        
        # Add the element ID to the result for direct clicking
        best_match['element_id'] = best_id    
        return best_match
        
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
        
    def save_element_mapping_to_file(self, filename: str = "element_mapping.json"):
        """Save the current element mapping to a file for later analysis"""
        breakpoint()
        if not self.element_mapping:
            self.highlight_clickable_elements()
            
        with open(filename, 'w') as f:
            json.dump(self.element_mapping, f, indent=2)
            
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

    def wait_for_text(self, text: str, timeout: int = 10, interval: float = 0.5):
        """Wait for text to appear on screen"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                return self.find_text_position(text)
            except:
                time.sleep(interval)
        raise TimeoutError(f"Text '{text}' did not appear within {timeout} seconds")


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
