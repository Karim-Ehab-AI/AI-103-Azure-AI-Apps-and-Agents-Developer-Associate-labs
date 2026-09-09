import os
import json
from dotenv import load_dotenv

# Import namespaces
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# 1. Define the mock database and local tool function
orders_db = {
    "ORD-101": {"status": "Shipped", "delivery_date": "Tomorrow", "items": ["Laptop", "Mouse"]},
    "ORD-202": {"status": "Processing", "delivery_date": "3 days", "items": ["Headphones"]},
}

def get_order_status(order_id: str) -> str:
    order = orders_db.get(order_id)
    if order:
        return json.dumps(order)
    return json.dumps({"error": "Order not found"})

def main(): 
    # Clear the console screen
    os.system('cls' if os.name == 'nt' else 'clear')

    try:
        # 2. Load configuration settings from the .env file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(script_dir, ".env"))

        azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")

        # 3. Initialize OpenAI client with Azure Entra ID authentication
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://ai.azure.com/.default"
        )

        openai_client = OpenAI(
            base_url=azure_openai_endpoint,
            api_key=token_provider
        )

        # 4. Define the tool specification (JSON schema) for the LLM
        tools = [
            {
                "type": "function",
                "name": "get_order_status",
                "description": "Retrieves the current status, delivery date, and items for a customer order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The unique order identifier, e.g., ORD-101",
                        }
                    },
                    "required": ["order_id"],
                },
            }
        ]

        # Track the previous response ID to maintain conversation state (memory)
        last_response_id = None

        print("🤖 AI Support Agent is ready! (Type 'quit' to exit)")

        # 5. Interactive chat loop
        while True:
            input_text = input("\nUser: ")
            if input_text.lower().strip() == "quit":
                break

            # Send prompt to the model and pass last_response_id to preserve conversation history
            response = openai_client.responses.create(
                model=model_deployment,
                input=input_text,
                tools=tools,
                instructions="You are a helpful customer support agent. Answer politely and concisely.",
                previous_response_id=last_response_id
            )

            # Update the response ID for the next conversation turn
            last_response_id = response.id
            
            tool_call_messages = []
            has_tool_call = False

            # 6. Check if the model requested any function calls
            for item in response.output:
                if item.type == "function_call" and item.name == "get_order_status":
                    has_tool_call = True
                    
                    # Parse the arguments provided by the model
                    args = json.loads(item.arguments)
                    order_id = args.get("order_id")
                    
                    # Execute the local function
                    status_result = get_order_status(order_id)
                    
                    # Format the tool output payload
                    tool_call_messages.append({
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": status_result
                    })

            # 7. If a tool was invoked, send the results back to the model for the final answer
            if has_tool_call:
                response = openai_client.responses.create(
                    model=model_deployment,
                    instructions="Formulate a user-friendly response based on the tool output.",
                    input=tool_call_messages,
                    tools=tools,
                    previous_response_id=last_response_id
                )
                # Update the response ID again after the follow-up response
                last_response_id = response.id

            # Print the final response to the user
            print(f"Agent: {response.output_text}")

    except Exception as ex:
        print(f"An error occurred: {ex}")

if __name__ == '__main__': 
    main()