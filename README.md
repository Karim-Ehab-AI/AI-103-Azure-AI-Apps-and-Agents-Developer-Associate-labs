# Azure AI Apps and Agents Developer Labs (AI-103)

## Overview

This repository contains hands-on lab exercises and code implementations designed for the Azure AI Apps and Agents Developer (AI-103) curriculum. The repository demonstrates how to develop, test, and run intelligent applications and agents powered by Microsoft Azure AI Foundry and Azure OpenAI Services.

Key topics and patterns covered across these labs include:

- Connecting Python applications to Azure OpenAI and Azure AI Foundry endpoints.
- Implementing passwordless authentication using Microsoft Entra ID and `azure-identity` (`DefaultAzureCredential`).
- Building conversational AI experiences using both the standard Chat Completions API and the newer Responses API.
- Implementing synchronous and asynchronous streaming chat interfaces.
- Integrating external data sources and tools (such as vector stores and document search over PDF brochures) to ground model responses.

## Repository Structure

```
AI-103-Azure-AI-Apps-and-Agents-Developer-Associate-labs/
|-- labs/
|   |-- chat-app/
|   |   |-- chat-app.py        # Synchronous chat application
|   |   |-- chat-async.py      # Asynchronous chat application
|   |   `-- requirements.txt   # Dependencies for the chat lab
|   `-- tools-app/
|       |-- brochures/         # PDF brochures used for grounding
|       |-- tools-app.py       # Application integrating tools and vector search
|       `-- requirements.txt   # Dependencies for the tools lab
`-- README.md                  # Project documentation
```

## Prerequisites

Before running the labs, ensure you have the following prerequisites in place:

1. **Python**: Python 3.10 or higher installed on your machine.
2. **Azure Subscription**: An active Azure subscription with access to Azure OpenAI or Azure AI Foundry.
3. **Model Deployment**: A deployed chat model (such as `gpt-4o` or `gpt-4o-mini`) in Azure AI Foundry / Azure OpenAI Studio.
4. **Azure CLI**: The Azure CLI installed to authenticate locally via `DefaultAzureCredential`.
5. **Role Permissions**: Your Azure account must have the **Cognitive Services OpenAI User** role assigned on your Azure OpenAI / Azure AI resource.

## Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Karim-Ehab-AI/AI-103-Azure-AI-Apps-and-Agents-Developer-Associate-labs.git
cd AI-103-Azure-AI-Apps-and-Agents-Developer-Associate-labs
```

### 2. Create and Activate a Virtual Environment

On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

You can install dependencies per lab. For example, for the chat app:

```bash
pip install -r labs/chat-app/requirements.txt
```

For the tools app:

```bash
pip install -r labs/tools-app/requirements.txt
```

### 4. Authenticate to Azure

These labs use token-based authentication via `DefaultAzureCredential`. Authenticate your local environment using the Azure CLI:

```bash
az login
```

If you have multiple Azure subscriptions, set your active subscription:

```bash
az account set --subscription "<your-subscription-id-or-name>"
```

### 5. Configure Environment Variables

Create a `.env` file in the root directory (or inside the individual lab directories) with the following environment variables:

```env
AZURE_OPENAI_ENDPOINT=https://<your-resource-name>.openai.azure.com/
MODEL_DEPLOYMENT=<your-model-deployment-name>
```

Replace `<your-resource-name>` with your actual Azure resource endpoint name, and `<your-model-deployment-name>` with your deployed model name (for example, `gpt-4o`).

## Running the Labs

### Lab 1: Generative AI Chat App (`labs/chat-app`)

This lab demonstrates how to build interactive conversational interfaces against Azure OpenAI.

#### Synchronous Chat (`chat-app.py`)

Highlights:
- Connects to Azure OpenAI using the `OpenAI` client with Entra ID bearer tokens.
- Supports both `chat.completions.create` and `responses.create` methods.
- Illustrates state tracking across turns using `previous_response_id`.
- Includes support for streaming responses in real time.

To run:
```bash
cd labs/chat-app
python chat-app.py
```

#### Asynchronous Chat (`chat-async.py`)

Highlights:
- Uses `AsyncOpenAI` and `azure.identity.aio.DefaultAzureCredential` for non-blocking asynchronous calls.
- Handles multi-turn chat loops asynchronously with proper session cleanup.

To run:
```bash
cd labs/chat-app
python chat-async.py
```

### Lab 2: Tools and Retrieval App (`labs/tools-app`)

This lab focuses on extending model capabilities using tools and retrieval-augmented generation (RAG) concepts.

Highlights:
- Working with local documents (PDF files in `labs/tools-app/brochures/`).
- Uploading documents to a vector store for search and retrieval.
- Grounding AI responses on custom organizational data.

To run:
```bash
cd labs/tools-app
python tools-app.py
```

## Security Best Practices

- **Passwordless Authentication**: Do not hardcode API keys in code or commit credentials to version control. The labs use Microsoft Entra ID tokens through `DefaultAzureCredential`.
- **Environment Management**: Keep `.env` files untracked by adding them to `.gitignore` (already configured in this repository).

## License

This project is intended for educational and lab training purposes as part of the AI-103 learning track.