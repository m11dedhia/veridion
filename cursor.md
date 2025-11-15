# AI QA Engineer – Daytona HackSprint Build Prompt (Browser Use Edition)

You are building a project called **AI QA Engineer**, a browser- and CLI-based QA automation tool for developers.  
It automatically runs *AI-driven browser tests* using **Browser Use**, logs failures to **Sentry**, and uses **LLMs (Claude or GPT-4)** to summarize and explain those failures.  
It runs entirely inside **Daytona** environments for instant, reproducible sandboxes.  
Optionally, it integrates **Galileo** for observability of the LLM test reasoning.

---

## 🎯 Goals
- Deliver a **working MVP** for the Daytona HackSprint SF 2025 hackathon.  
- Maximize eligibility for:  
  🥇 **Main prize**, 🏅 **Best Use of Daytona**, 🎖️ **Best Use of Sentry**, 🧠 **Best Use of Browser Use**.  
- Must demo live in <5 minutes: Daytona sandbox → AI browser agent → failure → Sentry log → LLM summary.

---

## 🧠 Product Summary
**AI QA Engineer** runs autonomous browser QA using an AI agent powered by Browser Use.  
It simulates human flows (login, checkout, navigation) directly in the browser — no brittle scripts.  
All tests run inside ephemeral **Daytona sandboxes**, log issues to **Sentry**, and get analyzed by **Claude or GPT-4** for human-readable insights.  
**Galileo** optionally logs the LLM traces for debugging.

---

## 🏗️ Architecture Overview
- **Core QA Engine:** Browser Use Python SDK (`Agent`, `Browser`, `ChatBrowserUse`)  
- **Cloud Dev Env:** Daytona workspace defined via `.devcontainer.json` + `docker-compose.yml`  
- **Error Monitoring:** Sentry (`sentry_sdk`)  
- **LLM Summarizer:** Claude or GPT-4 API call  
- **Optional Observability:** Galileo SDK for LLM traces  
- **Interfaces:** CLI (for automation) + Flask web UI (for demo dashboard)

---

## 📂 File Structure
ai-qa-engineer/
├── .devcontainer/devcontainer.json
├── docker-compose.yml
├── agent/qa_agent.py
├── sentry/init_sentry.py
├── llm_analysis/analyze_failure.py
├── cli.py
├── app.py
├── requirements.txt
└── README.md

---

## ⚙️ Implementation Details

### `.devcontainer/devcontainer.json`
```json
{
  "name": "AI QA Engineer",
  "dockerComposeFile": "../docker-compose.yml",
  "service": "tester",
  "workspaceFolder": "/workspace/ai-qa-engineer",
  "customizations": {
    "vscode": {
      "extensions": ["ms-python.python"]
    }
  },
  "postCreateCommand": "pip install -r requirements.txt"
}