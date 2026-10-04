import os
from urllib.request import urlopen, Request
import base64
from pathlib import Path
from dotenv import load_dotenv

# Add references
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:image/jpeg;base64,{encoded_string}"

def main(): 

    # Clear the console
    os.system('cls' if os.name=='nt' else 'clear')

    try: 
        # Get configuration settings 
        load_dotenv()
        openai_endpoint = os.getenv("ENDPOINT")
        model_deployment =  os.getenv("MODEL_DEPLOYMENT")

        # Create an OpenAI client
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
        client = OpenAI(
            base_url=openai_endpoint,
            api_key=token_provider()
        )

        # Initialize prompts
        system_message = "You are an AI assistant in a grocery store that sells fruit. You provide detailed answers to questions about produce."
        prompt = ""

        # Loop until the user types 'quit'
        while True:
            prompt = input("\nAsk a question about the image\n(or type 'quit' to exit)\n")
            if prompt.lower() == "quit":
                break
            elif len(prompt) == 0:
                    print("Please enter a question.\n")
            else:
                print("Getting a response ...\n")

                # Get a response to image input
                dir_path = Path(__file__).resolve().parent
                image_path = os.path.join(dir_path, "mystery-fruit.jpeg")

                if not os.path.exists(image_path):
                    print(f"Image is not exist in this dir: {image_path}")
                    return

                base64_image = encode_image(image_path)

                response = client.responses.create(
                    model=model_deployment,
                    input=[
                        {"role": "developer", "content": system_message},
                        { "role": "user", "content": [  
                            { "type": "input_text", "text": prompt},
                            { "type": "input_image", "image_url": base64_image}
                        ]} 
                    ]
                )
                print(response.output_text)

    except Exception as ex:
        print(ex)


if __name__ == '__main__': 
    main()