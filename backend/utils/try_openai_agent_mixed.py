import asyncio
import os
from openai import AsyncOpenAI
from agents import (
    Agent, 
    OpenAIChatCompletionsModel, 
    Runner, 
    set_tracing_disabled,
)
from dotenv import load_dotenv

load_dotenv(override=True)

# Disable tracing since we're not using OpenAI exclusively
set_tracing_disabled(disabled=False)

# Configure different clients
anthropic_client = AsyncOpenAI(
    base_url="https://api.anthropic.com/v1",  # Base URL without /chat/completions
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    default_headers={
        "anthropic-version": "2024-01-01",
        "content-type": "application/json",
    }
)

# Only create OpenAI client if we have an API key
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI(api_key=openai_api_key) if openai_api_key else None

async def run_agent(agent, message):
    """Run an agent with proper error handling."""
    try:
        result = await Runner.run(agent, message)
        print(f"{agent.name} says:", result.final_output)
        return True
    except Exception as e:
        print(f"Error with {agent.name}:", str(e))
        if isinstance(e, dict) and 'error' in e:
            print("API Error:", e['error'].get('message', 'Unknown error'))
        return False

async def main():
    # Create Claude agent
    claude_agent = Agent(
        name="Claude Assistant",
        instructions="You are Claude, a helpful assistant.",
        model=OpenAIChatCompletionsModel(
            model="claude-3-sonnet-20240229",
            openai_client=anthropic_client
        )
    )

    # Try Claude first
    print("Testing Claude integration:")
    await run_agent(claude_agent, "What's your name?")
    
    # Only try OpenAI if we have a valid API key
    if openai_client:
        print("\nTesting OpenAI integration:")
        gpt_agent = Agent(
            name="GPT Assistant",
            instructions="You are GPT-4, a helpful assistant.",
            model=OpenAIChatCompletionsModel(
                model="gpt-4o-mini",
                openai_client=openai_client
            )
        )
        await run_agent(gpt_agent, "What's your name?")
    else:
        print("\nSkipping OpenAI test - No valid API key found")
        print("To test OpenAI integration, please set OPENAI_API_KEY in your .env file")

if __name__ == "__main__":
    asyncio.run(main()) 