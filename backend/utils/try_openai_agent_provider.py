import asyncio
import os
from openai import AsyncOpenAI
from agents import (
    Agent,
    ModelSettings, 
    OpenAIChatCompletionsModel, 
    Runner, 
    set_tracing_disabled,
    ModelProvider,
    RunConfig
)
from dotenv import load_dotenv

from backend.utils.encoder import encode_image

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

image_path = "/Users/julienwuthrich/Downloads/17419048948108A44E8A7-C06D-46EE-A423-59FCC8506030-9080-00000523A7A9689A.jpg"
base64_image = encode_image(image_path)

agent = Agent(
    name="Assistant",
    model="gpt-4o",
    model_settings=ModelSettings(temperature=0.4, max_tokens=1024),
    instructions="Given an input image you will generate the description of the image in the style specified by the user."
)

async def main():
    result = await Runner.run(agent, input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Describe this image."},
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpg;base64,{base64_image}"
                },
            ]
        }
    ])
    print(result.final_output)

# async def main():
#     # Create the provider
#     provider = AnthropicProvider()
    
#     # Create agent without specifying client

#     # agent = Agent(
#     #     name="Claude Assistant",
#     #     instructions="You are a helpful assistant.",
#     #     model="claude-3-sonnet-20240229"  # Just specify the model name, provider will handle the rest
#     # )

#     try:
#         # Use the provider in RunConfig
#         result = await Runner.run(
#             agent, 
#             "Hello, how are you?",
#             run_config=RunConfig(model_provider=provider)
#         )
#         print(result.final_output)
#     except Exception as e:
#         print(f"Error details: {str(e)}")
#         if hasattr(e, 'response'):
#             print(f"Response: {await e.response.json()}")

if __name__ == "__main__":
    asyncio.run(main()) 