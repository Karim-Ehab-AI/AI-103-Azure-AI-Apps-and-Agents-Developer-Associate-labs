import os
import asyncio
import json
from dotenv import load_dotenv
from contextlib import AsyncExitStack
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
from openai.types.responses.response_input_param import FunctionCallOutput, ResponseInputParam

# Add references
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Clear the console
os.system('cls' if os.name=='nt' else 'clear')

# Load environment variables from .env file
load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

async def connect_to_server(exit_stack: AsyncExitStack):
    # Use absolute path so server.py is found regardless of working directory
    server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
    server_params = StdioServerParameters(
        command="python",
        args=[server_script],
        env=None
    )

    # Start the MCP server
    stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
    stdio, write = stdio_transport

    # Create an MCP client session
    session = await exit_stack.enter_async_context(ClientSession(stdio, write))
    await session.initialize()

    # List available tools
    response = await session.list_tools()
    tools = response.tools
    print("\nConnected to server with tools:", [tool.name for tool in tools]) 

    return session

async def chat_loop(session):

    # Connect to the agents client
    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):

        # Get the mcp tools available from the server
        response = await session.list_tools()
        tools = response.tools

        # Build a function for each tool
        def make_tool_func(tool_name):
            async def tool_func(**kwargs):
                result = await session.call_tool(tool_name, kwargs)
                return result

            tool_func.__name__ = tool_name
            return tool_func

        # Store the functions in a dictionary for easy access when processing function calls
        functions_dict = {tool.name: make_tool_func(tool.name) for tool in tools}

        # Create FunctionTool definitions for the agent
        mcp_function_tools: FunctionTool = []
        for tool in tools:
            function_tool = FunctionTool(
                name=tool.name,
                description=tool.description,
                parameters={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                strict=True
            )
            mcp_function_tools.append(function_tool)

        # Create the agent
        agent = project_client.agents.create_version(
            agent_name="inventory-agent",
            definition=PromptAgentDefinition(
                model=model_deployment,
                instructions="""
                You are an inventory assistant. Here are some general guidelines:
                - Recommend restock if item inventory < 10  and weekly sales > 15
                - Recommend clearance if item inventory > 20 and weekly sales < 5
                """,
                tools=mcp_function_tools
            ),
        )

        # Create a thread for the chat session
        conversation = openai_client.conversations.create()

        # Track the last response ID to chain turns correctly
        last_response_id = None

        while True:
            user_input = input("Enter a prompt for the inventory agent. Use 'quit' to exit.\nUSER: ").strip()
            if user_input.lower() == "quit":
                print("Exiting chat.")
                break

            # Send a prompt to the agent, chaining onto previous response if exists
            if last_response_id:
                response = openai_client.responses.create(
                    input=user_input,
                    previous_response_id=last_response_id,
                    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
                )
            else:
                response = openai_client.responses.create(
                    conversation=conversation.id,
                    input=user_input,
                    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
                )

            # Check the run status for failures
            if response.status == "failed":
                print(f"Response failed: {response.error}")
                continue

            # Process function calls - reset input_list each turn to avoid stale outputs
            input_list: ResponseInputParam = []
            for item in response.output:
                if item.type == "function_call":
                    # Retrieve the matching function tool
                    function_name = item.name
                    kwargs = json.loads(item.arguments)
                    required_function = functions_dict.get(function_name)

                    # Invoke the function
                    output = await required_function(**kwargs)

                    # Append the output text
                    input_list.append(
                    FunctionCallOutput(
                        type="function_call_output",
                        call_id=item.call_id,
                        output=output.content[0].text,
                    )
                    )

            # Send function call outputs back to the model and retrieve a response
            if input_list:
                response = openai_client.responses.create(
                        input=input_list,
                        previous_response_id=response.id,
                        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
                )

            # Save the final response ID for the next turn
            last_response_id = response.id
            print(f"Agent response: {response.output_text}")


        # Delete the agent when done
        print("Cleaning up agents:")
        project_client.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
        print("Deleted inventory agent.")


async def main():
    import sys
    exit_stack = AsyncExitStack()
    try:
        session = await connect_to_server(exit_stack)
        await chat_loop(session)
    finally:
        await exit_stack.aclose()

if __name__ == "__main__":
    asyncio.run(main())
