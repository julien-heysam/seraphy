import asyncio
import os
from openai import AsyncOpenAI
from agents import (
    Agent, 
    OpenAIChatCompletionsModel, 
    Runner, 
    set_tracing_disabled,
    ModelProvider,
    RunConfig
)
from dotenv import load_dotenv

load_dotenv(override=True)

# Disable tracing since we're not using OpenAI
set_tracing_disabled(disabled=True)

# Create a custom provider
class AnthropicProvider(ModelProvider):
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://api.anthropic.com/v1",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            default_headers={
                "anthropic-version": "2024-01-01",
                "content-type": "application/json",
            }
        )

    def get_client(self, model: str) -> AsyncOpenAI:
        return self.client

    def get_model(self, model: str) -> OpenAIChatCompletionsModel:
        return OpenAIChatCompletionsModel(
            model=model,
            openai_client=self.client
        )

async def main():
    # Create the provider
    provider = AnthropicProvider()
    
    # Create agent without specifying client
    agent = Agent(
        name="Claude Assistant",
        instructions="You are a helpful assistant.",
        model="claude-3-sonnet-20240229"  # Just specify the model name, provider will handle the rest
    )

    try:
        # Use the provider in RunConfig
        result = await Runner.run(
            agent, 
            "Hello, how are you?",
            run_config=RunConfig(model_provider=provider)
        )
        print(result.final_output)
    except Exception as e:
        print(f"Error details: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Response: {await e.response.json()}")

if __name__ == "__main__":
    asyncio.run(main()) 