import os

from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel
from dotenv import load_dotenv

load_dotenv(override=True)


anthropic_client = AsyncOpenAI(
    base_url="https://api.anthropic.com/v1", 
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    default_headers={
        "anthropic-version": "2024-01-01",
        "content-type": "application/json",
    }
)
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

instruction = """
Identify the clickable element associated with the `target_text`.
All clickable elements are numbered and highlighted with colored borders. 
Return the NUMBER of the element that contains this text. 
If the element is not found, respond with 'idk'.

# Output Format

- A single number representing the clickable element containing the text.
- If the element is not found, respond with 'idk'.

# Notes

- Ensure text matching is accurate; only return a number if the text in the element matches the `target_text`.
- Consider case sensitivity and whitespace processing if relevant.
"""

claude_browser_agent = Agent(
    name="Claude Browser OCR",
    instructions=instruction,
    model=OpenAIChatCompletionsModel(model="claude-3-7-sonnet-20250219", openai_client=anthropic_client),
    # tools=[bash_command],
)

openai_browser_agent = Agent(
    name="OpenAI Browser OCR",
    instructions=instruction,
    model=OpenAIChatCompletionsModel(model="gpt-4o", openai_client=openai_client),
    # tools=[bash_command],
)


instruction_v2 = """
Based on the provided screenshot and json user_actions file, determine the appropriate user action, which may involve clicking an element or entering text on a webpage.
You must return the element NUMBER that we should do an action on.

All clickable elements are numbered and highlighted with colored borders. 
If the element is not found, respond with 'idk'.

# Output Format
{
    "element_number": int,
    "type": str <click, input, mousemove, navigation, input_text, etc.>
}
- If the element is not found, respond with 'idk'.

ONLY RETURN THE JSON OBJECT.
"""

claude_browser_agent_v2 = Agent(
    name="Claude Browser OCR",
    instructions=instruction_v2,
    model=OpenAIChatCompletionsModel(model="claude-3-7-sonnet-20250219", openai_client=anthropic_client),
    # tools=[bash_command],
)

openai_browser_agent_v2 = Agent(
    name="OpenAI Browser OCR",
    instructions=instruction_v2,
    model=OpenAIChatCompletionsModel(model="gpt-4o", openai_client=openai_client),
    # tools=[bash_command],
)


instruction_v3 = """
Based on the provided screenshot and json user_actions file, determine the appropriate user action, which may involve clicking an element or entering text on a webpage.
You must return the COORDINATES of the element that we should do an action on.

All clickable elements are numbered and highlighted with colored borders. 
If the element is not found, respond with 'idk'.

# Output Format
{
    "coordinates": {"x": int, "y": int},
    "type": str <click, input, mousemove, navigation, input_text, etc.>
}
- If the element is not found, respond with 'idk'.

ONLY RETURN THE JSON OBJECT.
""" 

claude_browser_agent_v3 = Agent(
    name="Claude Browser OCR",
    instructions=instruction_v3,
    model=OpenAIChatCompletionsModel(model="claude-3-7-sonnet-20250219", openai_client=anthropic_client),
    # tools=[bash_command],
)

openai_browser_agent_v3 = Agent(
    name="OpenAI Browser OCR",
    instructions=instruction_v3,
    model=OpenAIChatCompletionsModel(model="gpt-4o", openai_client=openai_client),
    # tools=[bash_command],
)
