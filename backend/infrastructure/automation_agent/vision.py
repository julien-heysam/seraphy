import asyncio
import json
import logging
import os
from typing import Any, Optional

from agents import Runner
from pydantic import BaseModel
import requests
import urllib3

from backend import PROJECT_PATHS
from backend.infrastructure.automation_agent.base import AutomationAgent
from backend.infrastructure.enhanced_browser.factory import BrowserProviderType, EnhancedBrowserFactory
from backend.core.agents.browser import claude_browser_agent, openai_browser_agent, claude_browser_agent_v2, openai_browser_agent_v2, claude_browser_agent_v3, openai_browser_agent_v3
from backend.utils.encoder import encode_image

logger = logging.getLogger(__name__)

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
session.mount('http://', adapter)
session.mount('https://', adapter)

urllib3.PoolManager(maxsize=10)  # Increase max connections to 10
# Or for specific hosts:
urllib3.connectionpool.HTTPConnectionPool.maxsize = 10

class Step(BaseModel):
    action: str
    url: str = None
    value: str = None
    xpath: str = None
    wait_after: int = 0
    element_id: int = None
    field_name: str = None
    description: str = None


class VisionAutomationAgent(AutomationAgent):
    def __init__(self):
        self.browser = EnhancedBrowserFactory.create(BrowserProviderType.SELENIUM)
        self.element_mapping = {}

    async def find_element_by_field_name(self, screenshot_path: str, field_name: str) -> int:
        base64_image = encode_image(screenshot_path)
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text", 
                        "text": f"The `target_text` is '{field_name}'."
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{base64_image}",
                        "detail": "high"
                    },
                ]
            }
        ]
        try:
            result = await Runner.run(claude_browser_agent, input=messages)
        except Exception as e:
            logger.debug("Error finding with claude, trying with openai")
            result = await Runner.run(openai_browser_agent, input=messages)

        return result.final_output

    async def find_element_by_xy(self, screenshot_path: str, action: str) -> int:
        base64_image = encode_image(screenshot_path)
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text", 
                        "text": f"Based on the screenshot provided, and the json object can you what are the location x, y and the type of action to take (click, input_text, mousseover, navigation, ...)? The action is {str(action)}"
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{base64_image}",
                        "detail": "high"
                    },
                ]
            }
        ]
        try:
            result = await Runner.run(openai_browser_agent_v3, input=messages)
        except Exception as e:
            logger.debug("Error finding with openai, trying with claude")
            result = await Runner.run(claude_browser_agent_v3, input=messages)

        return result.final_output

    async def find_element_by_action(self, screenshot_path: str, action: str) -> int:
        base64_image = encode_image(screenshot_path)
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text", 
                        "text": f"Based on the screenshot provided, and the json object can you tell me what should be the action to take? The action is {str(action)}"
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{base64_image}",
                        "detail": "high"
                    },
                ]
            }
        ]
        try:
            result = await Runner.run(openai_browser_agent_v2, input=messages)
        except Exception as e:
            logger.debug("Error finding with openai, trying with claude")
            result = await Runner.run(claude_browser_agent_v2, input=messages)

        return result.final_output

    async def click_first_approach(self, action: dict):
        field = action['field_name']
        element_info = self.browser.get_element_by_text(field)
        if element_info:
            if 'element_id' in element_info:
                element_id = int(element_info['element_id'])
                self.browser.click_element_by_number(element_id)
            else:
                self.click_at_position(element_info['x'], element_info['y'])
            if 'wait_after' in action:
                await asyncio.sleep(action['wait_after'])
        else:
            raise Exception(f"Element not found: {field}")

    async def click_second_approach(self, action: dict):
        field = action['field_name']
        screenshot_path, screenshot = self.browser.get_screenshot()
        llm_response = await self.find_element_by_text(screenshot_path, field)
        if llm_response and "idk" not in llm_response:
            element_id = int(llm_response['element_id'])
            self.browser.click_element_by_number(element_id)
            if 'wait_after' in action:
                await asyncio.sleep(action['wait_after'])
        else:
            raise Exception(f"Element not found: {field}")

    async def click(self, action: dict):
        try:
            await self.click_first_approach(action)
        except Exception as e:
            logger.debug("Error clicking with first approach, trying with second approach")
            try:
                await self.click_second_approach(action)
            except Exception as e:
                raise Exception(f"Error clicking with second approach: {e}. Closing browser.")

    async def input_text_first_approach(self, action: dict):
        field = action['field_name']
        element_info = self.browser.get_element_by_text(field)
        if element_info:
            if 'element_id' in element_info:
                self.click_element_by_number(int(element_info['element_id']))
            else:
                self.click_at_position(element_info['x'], element_info['y'])
            if 'wait_after' in action:
                await asyncio.sleep(action['wait_after'])
        else:
            raise Exception(f"Element not found: {field}")

    async def input_text_second_approach(self, action: dict):
        field = action['field_name']
        screenshot_path, screenshot = self.browser.get_screenshot()
        llm_response = await self.find_element_by_text(screenshot_path, field)
        if llm_response and "idk" not in llm_response:
            element_id = int(llm_response['element_id'])
            self.browser.click_element_by_number(element_id)
            if 'wait_after' in action:
                await asyncio.sleep(action['wait_after'])
        else:
            raise Exception(f"Element not found: {field}")

    async def input_text(self, action: dict):
        try:
            await self.input_text_first_approach(action)
        except Exception as e:
            logger.debug("Error inputting text with first approach, trying with second approach")
            try:
                await self.input_text_second_approach(action)
            except Exception as e:
                raise Exception(f"Error inputting text with second approach: {e}. Closing browser.")
        self.browser.type_text(action['value'])

    async def execute_action(self, action: dict):
        action_type = action['action']
        element = None
        match action_type:
            case 'navigate':
                self.browser.navigate_to(action['url'])
                self.browser.highlight_clickable_elements()
            case 'click':
                await self.click(action)
            case 'click_element_number':
                self.browser.click_element_by_number(action['element_id'])
                if 'wait_after' in action:
                    await asyncio.sleep(action['wait_after'])
            case 'input_text':
                await self.input_text(action)
            case 'mousemove':
                ...
            case 'mouse_hover':
                ...
            case 'wait':
                await asyncio.sleep(action['wait_after'])
            case 'move_to_element_xpath':
                element = self.browser.move_to_element_xpath(action)
            case 'click_element':
                if element:
                    self.browser.click_element(element)
                else:   
                    raise Exception("Element not found, `click_element` action failed")
            case 'input_text':
                self.browser.type_text(action['value'])
    
    async def run_demo(self, action: dict, element = None) -> tuple[bool, Optional[Any]]:
        worked = False
        element_under_cursor = action.get('elementUnderCursor')

        ## Move to element
        if element_under_cursor:
            try:
                element = self.browser.move_to_element_xpath(element_under_cursor)
                worked = True
                return worked, element
            except Exception as e:
                try:
                    element = self.browser.get_element_by_text(element_under_cursor['text'])
                    worked = True
                    return worked, element
                except Exception as e:
                    logger.error(f"Element not found: {element_under_cursor['text']}")
                    return worked, None

        ## Navigation
        if action.get('type') == 'navigation':
            if element:
                element.click()
                worked = True
            else:
                logger.error(f"Click on element failed, {action}")
                if "to_url" in action:
                    self.browser.navigate_to(action['to_url'])
                    worked = True

        ## Click
        if action.get('type') == 'click':
            if element:
                element.click()
                worked = True
            elif "element" in action:
                try:
                    element = action.get("element", {}).get("xpath")
                    element = self.browser.move_to_element_xpath(action.get("element", {}))
                    if element:
                        self.browser.click_element(element)
                        worked = True
                    else:
                        logger.error(f"Element not found: {action}")

                except Exception as e:
                    logger.error(f"Element not found: {action}")
                    try:
                        position = action.get('position', {})
                        x = position.get('x')
                        y = position.get('y')
                        
                        if x is not None and y is not None:
                            # Move cursor to the specified position
                            self.browser.move_mouse_to(x, y)
                            self.browser.click_at_position(x, y)
                            worked = True
                    except Exception as e:
                        logger.error(f"Failed to move mouse: {e}")
            else:
                breakpoint()
        
        ## Mouse move
        if action.get('type') == 'mousemove':
            try:
                # Get the position coordinates from the action
                position = action.get('position', {})
                x = position.get('x')
                y = position.get('y')
                
                if x is not None and y is not None:
                    # Move cursor to the specified position
                    self.browser.move_mouse_to(x, y)
                    logger.info(f"Mouse moved to position: ({x}, {y})")
                    worked = True
                else:
                    logger.error(f"Invalid mousemove action: missing coordinates in {action}")
            except Exception as e:
                logger.error(f"Failed to move mouse: {e}")

        ## Wait
        if action.get('type') == 'wait':
            await asyncio.sleep(action['wait_after'])
            worked = True

        ## Input text
        if action.get('type') == 'input_text':
            breakpoint()

        ## Click element by text
        if not worked:
            field = action.get('field_name')
            screenshot_path, screenshot = self.browser.get_screenshot()
            if field:
                llm_response = await self.find_element_by_field_name(screenshot_path, field)
                if llm_response and "idk" not in llm_response:
                    element_id = int(llm_response['element_id'])
                    self.browser.click_element_by_number(element_id)
                    worked = True
                    if 'wait_after' in action:
                        await asyncio.sleep(action['wait_after'])
                else:
                    logger.error(f"Element not found: {field}")
                    llm_response = await self.find_element_by_action(screenshot_path, action)
            else:
                llm_response = await self.find_element_by_action(screenshot_path, action)
                if llm_response and "idk" not in llm_response:
                    breakpoint()
                    try:
                        if llm_response.startswith("```json"):
                            json_response = json.loads(llm_response[7:-3])
                        else:
                            json_response = json.loads(llm_response)

                        logger.info("LLM response: " + str(llm_response))
                        try:
                            self.browser.click_element_by_number(json_response['element_number'])
                            worked = True
                            if 'wait_after' in action:
                                await asyncio.sleep(action['wait_after'])
                        except Exception as e:
                            logger.error(f"Failed to click element: {e}")
                    except Exception as e:
                        logger.error(f"Failed to parse LLM response: {e}")
                else:
                    logger.error(f"Element not found: {action}")
        
        if not worked:
            logger.warning(f"Trying again with agent")
            llm_response = await self.find_element_by_xy(screenshot_path, action)
            if llm_response and "idk" not in llm_response:
                breakpoint()
                if llm_response.startswith("```json"):
                    json_response = json.loads(llm_response[7:-3])
                else:
                    json_response = json.loads(llm_response)
                logger.info("LLM response: " + str(llm_response))
                try:
                    self.browser.move_mouse_to(**llm_response['coordinates'])
                    worked = True
                    if 'wait_after' in action:
                        await asyncio.sleep(action['wait_after'])
                except Exception as e:
                    logger.error(f"Failed to click element: {e}")

        return worked, None

    async def run(self, action_log_path: list[dict]):
        try:
            self.browser.navigate_to("https://www.heysam.ai/")
            steps = self.load_action_log(action_log_path)
            element = None
            for step in steps:
                worked, element = await self.run_demo(step, element)
        finally:
            # Make sure to close the browser when done
            # self.browser.close()
            pass

if __name__ == "__main__":
    action_log_path = os.path.join(PROJECT_PATHS.RAW_DATA, 'recordings', 'action_logs', 'user_actions_20250317_235434.json')
    asyncio.run(VisionAutomationAgent().run(action_log_path))
