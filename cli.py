import sys

from config import settings
from agent import LLMClient, ResearchScoutAgent
from tools import TavilySearchTool


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python cli.py "Your research question here"')
        return 1

    question = " ".join(sys.argv[1:]).strip()

    if not question:
        print("Error: Empty query provided.")
        return 1

    llm = LLMClient()

    search_tool = TavilySearchTool(
        api_key=settings.tavily_api_key,
    )

    agent = ResearchScoutAgent(
        llm=llm,
        search_tool=search_tool,
    )

    try:
        result = agent.run(question)

        # Raw JSON output (best for debugging and testing)
        print(result.model_dump_json(indent=2))

        return 0

    except Exception as e:
        print(f"Agent Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())