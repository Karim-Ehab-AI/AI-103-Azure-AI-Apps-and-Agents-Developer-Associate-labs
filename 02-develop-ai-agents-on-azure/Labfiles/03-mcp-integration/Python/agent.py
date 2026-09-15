import os
from dotenv import load_dotenv

# Add references
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, MCPTool
from openai.types.responses.response_input_param import McpApprovalResponse, ResponseInputParam

# Clear the CLI
os.system('cls' if os.name == 'nt' else 'clear')

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

# Connect to the agents client
with (
    DefaultAzureCredential() as credential,
    AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client,
    project_client.get_openai_client() as openai_client,
):

    # Initialize agent MCP tool
    mcp_tool = MCPTool(
        server_label="api-specs",
        server_url="https://learn.microsoft.com/api/mcp",
        require_approval="always",
    )

    # Create a new agent with the MCP tool
    agent = project_client.agents.create_version(
        agent_name="MyAgent",
        definition=PromptAgentDefinition(
            model=model_deployment,
            instructions="You are a helpful agent that can use MCP tools to assist users. Use the available MCP tools to answer questions and perform tasks.",
            tools=[mcp_tool],
        ),
    )
    print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

    # Create a conversation thread
    conversation = openai_client.conversations.create()
    print(f"Created conversation (id: {conversation.id})")

    print("-" * 40)
    print("Agent: Hi, How can I help you today? :) --> Need to leave? Enter (quit).")

    # Track the last response ID to chain conversation turns correctly
    last_response_id = None

    while True:
        input_text = input("\nUser: ").strip().lower()
        if input_text == "quit":
            break

        # Build the initial request; chain onto the previous response if one exists
        # so the API knows the full conversation history and has no pending approvals
        create_kwargs = {
            "input": input_text,
            "extra_body": {"agent_reference": {"name": agent.name, "type": "agent_reference"}},
        }
        if last_response_id:
            create_kwargs["previous_response_id"] = last_response_id
        else:
            create_kwargs["conversation"] = conversation.id

        response = openai_client.responses.create(**create_kwargs)

        # Process any MCP approval requests that were generated
        # The agent may issue several tool calls, each needing its own approval,
        # so we loop until there are none left.
        while True:
            # Collect any MCP approval requests from the latest response
            input_list: ResponseInputParam = []
            for item in response.output:
                if item.type == "mcp_approval_request":
                    if item.server_label == "api-specs" and item.id:
                        approval_response = input(f"\nAgent: I need approval to call ({item.id}). Do you approve? (y/n)\nUser: ")

                        while approval_response not in ("y", "n"):
                            approval_response = input("\nAgent: Invalid input. Please enter (y/n) ONLY.\nUser: ").strip().lower()

                        input_list.append(
                            McpApprovalResponse(
                                type="mcp_approval_response",
                                approve=approval_response == "y",
                                approval_request_id=item.id,
                            )
                        )

            # No more approvals needed -> the agent has produced its final response
            if not input_list:
                break

            # Send the approval response back and retrieve the next response
            response = openai_client.responses.create(
                input=input_list,
                previous_response_id=response.id,
                extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            )

        # Save the final response ID so the next user turn chains correctly
        last_response_id = response.id

        print(f"\nAgent response: {response.output_text}")

    # Clean up resources by deleting the agent version
    project_client.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
    print("Agent deleted")
