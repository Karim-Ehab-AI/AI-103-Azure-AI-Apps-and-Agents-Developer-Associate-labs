from dotenv import load_dotenv
import os

# import namespaces
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from openai.types.responses.response_input_param import McpApprovalResponse


def main():
    try:
        # Clear the console
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Get Configuration Settings
        load_dotenv()
        foundry_endpoint = os.getenv('FOUNDRY_ENDPOINT')
        agent_name = os.getenv('AGENT_NAME')

        # Get project client
        project_client = AIProjectClient(
            endpoint=foundry_endpoint,
            credential=DefaultAzureCredential(),
        )

        # Get an OpenAI client
        openai_client = project_client.get_openai_client()

        # Use the agent to get a response
        prompt = input("User prompt: ")
        response = openai_client.responses.create(
            input=[{"role": "user", "content": prompt}],
            extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
        )

        # Check for MCP approval requests
        for item in response.output:
            if item.type == "mcp_approval_request":
                mcp_approval = McpApprovalResponse(
                    type="mcp_approval_response",
                    approve=True,
                    approval_request_id=item.id,
                )

        response = openai_client.responses.create(
                    input=[mcp_approval],
                    previous_response_id=response.id,
                    extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
                )

        print(f"{agent_name}: {response.output_text}")

        
    except Exception as ex:
        print(ex)

if __name__ == "__main__":
    main()