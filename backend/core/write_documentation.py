import asyncio

from agents import Agent, Runner

from backend.core.tools.bash_command import bash_command
from backend.core.agents.documentarian import claude_documentation_agent, openai_documentation_agent
from backend.core.agents.tester import claude_tester_agent, openai_tester_agent

triage_agent = Agent(
    name="Triage agent",
    instructions="Handoff to the appropriate agent based on the language of the request.",
    handoffs=[claude_tester_agent, claude_documentation_agent],
    tools=[bash_command],
)


async def main():
    result = await Runner.run(triage_agent, input="""Write documentation for the following code:  
```
import asyncio

from agents import Agent, Runner, function_tool


@function_tool
def get_weather(city: str) -> str:
    return f"The weather in {city} is sunny."


agent = Agent(
    name="Hello world",
    instructions="You are a helpful agent.",
    tools=[get_weather],
)


async def main():
    result = await Runner.run(agent, input="What's the weather in Tokyo?")
    print(result.final_output)
    # The weather in Tokyo is sunny.


if __name__ == "__main__":
    asyncio.run(main())```
""")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
