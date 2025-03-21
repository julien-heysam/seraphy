import os

from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel
from dotenv import load_dotenv

from backend.core.tools import bash_command

load_dotenv(override=True)


anthropic_client = AsyncOpenAI(
    base_url="https://api.anthropic.com/v1",  # Base URL without /chat/completions
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    default_headers={
        "anthropic-version": "2024-01-01",
        "content-type": "application/json",
    }
)
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

instructions="""
You are a OCR agent. You will be given an image and you will need to extract the text from the image.
"""

claude_ocr_agent = Agent(
    name="Claude OCR",
    instructions=instructions,
    model=OpenAIChatCompletionsModel(model="claude-3-7-sonnet-20250219", openai_client=anthropic_client),
    tools=[bash_command],
)

openai_ocr_agent = Agent(
    name="OpenAI OCR",
    instructions=instructions,
    model=OpenAIChatCompletionsModel(model="gpt-4o", openai_client=openai_client),
    tools=[bash_command],
)
