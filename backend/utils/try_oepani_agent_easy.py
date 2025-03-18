# import os
# from dotenv import load_dotenv
# load_dotenv(override=True)
# import agentops
# agentops.init(os.getenv("AGENT_OPS_API_KEY"))

# from agents import Agent, Runner, trace
# agent = Agent(name="Assistant", instructions="You are a helpful assistant")
# with trace("Joke workflow"):
#     result = Runner.run_sync(agent, "Write a haiku about recursion in programming.")
# print(result.final_output)



# import asyncio
# import os
# from dotenv import load_dotenv

# load_dotenv()

# from agents import Agent, Runner, function_tool
# # import agentops

# # agentops.init(api_key=os.getenv("AGENT_OPS_API_KEY"))

# @function_tool
# def get_weather(city: str) -> str:
#     return f"The weather in {city} is sunny."


# agent = Agent(
#     name="Hello world",
#     instructions="You are a helpful agent.",
#     tools=[get_weather],
# )


# async def main():
#     result = await Runner.run(agent, 
#                               input="What's the weather in San Francisco?")
#     print(result.final_output)
#     # The weather in San Francisco is sunny.


# if __name__ == "__main__":
#     asyncio.run(main())
