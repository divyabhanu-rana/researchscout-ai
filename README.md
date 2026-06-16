# ResearchScout AI

Agentic Learning and Research Assistant for AI/ML Students

## Features

- Multi-stage Agent Workflow
  - Observe
  - Reason
  - Decide
  - Act
  - Reflect
  - Respond

- Dynamic Search Routing
- Tavily Web Search
- DeepSeek LLM Integration
- Reflection & Self-Correction
- Streamlit Interface

## Architecture

```mermaid
flowchart TD
    A[User Query] --> B[Decision Agent]
    B --> C{Need Search?}

    C -->|No| D[Synthesis]
    C -->|Yes| E[Tavily Search]

    E --> D
    D --> F[Reflection]
    F --> G[Final Response]
```

## Installation

pip install -r requirements.txt

## Environment Variables

Copy:

.env.example

to

.env

and fill in:

DEEPSEEK_API_KEY=
TAVILY_API_KEY=

## Run

streamlit run app.py
