# Lab 01: Build AI Agents with Portal and VS Code

This lab demonstrates how to build and interact with an AI agent using both the **Microsoft Foundry Portal** and **Visual Studio Code** (Python SDK).

---

## 🔗 Official Links & Resources

- 📖 **Lab Instructions:** [Build AI agents with portal and VS Code](https://microsoftlearning.github.io/mslearn-ai-agents/Instructions/Exercises/01-build-agent-portal-and-vscode.html)
- 🎓 **Learning Path / Module:** [Develop AI agents in Azure with Visual Studio Code](https://learn.microsoft.com/en-us/training/modules/develop-ai-agents-azure-vs-code/)

---

## 🎯 Lab Overview

In this exercise, you:
1. **Create an AI Agent in Microsoft Foundry Portal**:
   - Provision a Microsoft Foundry project and model deployment.
   - Create an agent named `it-support-agent`.
   - Configure agent system instructions for an IT Support role.
2. **Ground the Agent with Enterprise Data & Tools**:
   - Add the **File Search** tool and upload `IT_Policy.txt` to ground responses in corporate policies.
   - Add the **Code Interpreter** tool and upload `system_performance.csv` for data analysis and chart generation.
3. **Interact Programmatically via Python (VS Code)**:
   - Use the `azure-ai-projects` SDK (`AIProjectClient`) to retrieve the agent by name.
   - Create conversations and run interactive chat sessions directly from the terminal.
   - Retrieve and save generated files and visualization charts locally in `agent_outputs/`.

---

## 📁 Repository Structure

```text
01-build-agent-portal-and-vscode/
├── README.md                 # Lab overview and instructions guide (this file)
├── IT_Policy.txt             # Policy document for grounding (File Search tool)
├── system_performance.csv    # Performance dataset for Code Interpreter analysis
└── Python/
    ├── agent_with_functions.py  # Python script to connect and chat with the agent
    ├── requirements.txt         # Required Python packages (azure-ai-projects, etc.)
    ├── .env.example             # Example environment configuration template
    └── .env                     # Local environment file (with your project endpoint)
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Azure Subscription** with access to Microsoft Foundry (Azure AI Foundry).
- **Python 3.13** installed on your local machine.
- **Azure CLI** installed.

### 2. Sign in to Azure
```powershell
az login
```

### 3. Setup Virtual Environment
Navigate to the `Python/` directory:
```powershell
cd Python
python -m venv labenv
.\labenv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and configure your settings:
```powershell
cp .env.example .env
```
Inside `.env`:
```env
PROJECT_ENDPOINT=<your_foundry_project_endpoint>
AGENT_NAME=it-support-agent
```

### 5. Run the Application
```powershell
python agent_with_functions.py
```
Type your queries in the terminal (e.g. asking about IT policies or requesting performance analysis based on the CSV data). Output charts and generated files will be saved in `agent_outputs/`. Type `exit` to end the session.

