from __future__ import annotations

import json
from typing import List, Type, TypeVar

from ollama import chat
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from config import settings
from models import (
    AgentRunOutput,
    ReflectionReview,
    ResearchResponse,
    SearchDecision,
    SearchResult,
)
from prompts import (
    JSON_REPAIR_PROMPT,
    REFLECTION_PROMPT,
    REVISION_PROMPT,
    SEARCH_DECISION_PROMPT,
    SYSTEM_PROMPT,
    SYNTHESIS_NO_SEARCH_PROMPT,
    SYNTHESIS_WITH_SEARCH_PROMPT,
)
from tools import TavilySearchTool

T = TypeVar("T", bound=BaseModel)

DEBUG = False


class LLMClient:

    def __init__(self):

        self.provider = settings.llm_provider

        if self.provider == "deepseek":

            self.client = OpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
            )

    def json_chat(
        self,
        *,
        model: str,
        system: str,
        user: str,
        timeout_s: int,
    ) -> str:

        if self.provider == "ollama":

            response = chat(
                model=settings.ollama_model,
                messages=[
                    {
                        "role": "system",
                        "content": system,
                    },
                    {
                        "role": "user",
                        "content": user,
                    },
                ],
            )

            return response["message"]["content"]

        elif self.provider == "deepseek":

            response = self.client.chat.completions.create(
                model=settings.deepseek_model,
                messages=[
                    {
                        "role": "system",
                        "content": system,
                    },
                    {
                        "role": "user",
                        "content": user,
                    },
                ],
                temperature=0.2,
            )

            return response.choices[0].message.content or ""

        else:

            raise ValueError(
                f"Unsupported LLM provider: {self.provider}"
            )


class ResearchScoutAgent:
    """
    Core Agent Orchestrator

    Observe
    → Reason
    → Decide
    → Act
    → Reflect
    → Respond
    """

    def __init__(
        self,
        llm: LLMClient,
        search_tool: TavilySearchTool,
    ):
        self.llm = llm
        self.search_tool = search_tool

    def _parse_model(
        self,
        model_cls: Type[T],
        raw: str,
    ) -> T:

        cleaned = raw.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]

        if cleaned.startswith("```"):
            cleaned = cleaned[3:]

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        return model_cls.model_validate_json(cleaned)

    def _ask_and_parse(
        self,
        *,
        model_cls: Type[T],
        user_prompt: str,
        schema_hint: str,
    ) -> T:

        raw = self.llm.json_chat(
            model=settings.ollama_model,
            system=SYSTEM_PROMPT,
            user=user_prompt,
            timeout_s=settings.request_timeout_s,
        )

        # --------------------------------------------------
        # DEBUG OUTPUT
        # --------------------------------------------------

        if DEBUG:
            print("\n" + "=" * 70)
            print("RAW LLM OUTPUT")
            print("=" * 70)
            print(raw)
            print("=" * 70 + "\n")

        try:
            return self._parse_model(model_cls, raw)

        except (ValidationError, ValueError):

            if settings.llm_max_retries <= 0:
                raise

            repair_prompt = JSON_REPAIR_PROMPT.format(
                schema_hint=schema_hint,
                bad_output=raw,
            )

            repaired_raw = self.llm.json_chat(
                model=settings.ollama_model,
                system=SYSTEM_PROMPT,
                user=repair_prompt,
                timeout_s=settings.request_timeout_s,
            )

            if DEBUG:
                print("\n" + "=" * 70)
                print("REPAIRED LLM OUTPUT")
                print("=" * 70)
                print(repaired_raw)
                print("=" * 70 + "\n")

            try:
                return self._parse_model(
                    model_cls,
                    repaired_raw,
                )

            except (ValidationError, ValueError) as e:
                raise RuntimeError(
                    f"Failed to parse {model_cls.__name__} after repair attempt."
                ) from e

    @staticmethod
    def _heuristic_need_search(question: str) -> bool:
        q = question.lower()

        triggers = [
            "latest",
            "recent",
            "this year",
            "2025",
            "2026",
            "trends",
            "job",
            "jobs",
            "internship",
            "internships",
            "demand",
            "hiring",
            "salary",
            "market",
            "in india",
            "papers",
            "state of the art",
            "sota",
            "release",
            "released",
            "announced",
            "today",
            "now",
        ]

        return any(trigger in q for trigger in triggers)

    def run(self, question: str) -> AgentRunOutput:

        question = (question or "").strip()

        # --------------------------------------------------
        # Empty Input
        # --------------------------------------------------

        if not question:

            decision = SearchDecision(
                need_search=False,
                reason="Empty question provided.",
            )

            response = ResearchResponse(
                query_type="no_search",
                summary="Please provide a non-empty question.",
                key_findings=[],
                recommended_next_steps=[
                    "Try asking: Explain RAG with an example."
                ],
                sources=[],
            )

            reflection = ReflectionReview(
                is_complete=True,
                has_sources_when_needed=True,
                is_educational=True,
                should_revise=False,
                revision_notes=[],
            )

            return AgentRunOutput(
                user_query="",
                decision=decision,
                tool_used="none",
                search_results=[],
                response=response,
                reflection=reflection,
            )

        # --------------------------------------------------
        # Decision Layer
        # --------------------------------------------------

        decision = self._ask_and_parse(
            model_cls=SearchDecision,
            user_prompt=SEARCH_DECISION_PROMPT.format(
                question=question
            ),
            schema_hint="""
            {
                "need_search": true,
                "reason": "Recent information required."
            }
            """,
        )

        heuristic = self._heuristic_need_search(question)

        if heuristic and not decision.need_search:
            decision = SearchDecision(
                need_search=True,
                reason=(
                    f"{decision.reason} "
                    "(Heuristic override: appears time-sensitive.)"
                ),
            )

        # --------------------------------------------------
        # Search Layer
        # --------------------------------------------------

        search_results: List[SearchResult] = []
        tool_used = "none"

        if decision.need_search:
            tool_used = "tavily"

            search_results = self.search_tool.search(
                question,
                max_results=settings.max_search_results,
            )

        # --------------------------------------------------
        # Synthesis Layer
        # --------------------------------------------------

        if decision.need_search and search_results:

            search_json = json.dumps(
                [
                    result.model_dump(mode="json")
                    for result in search_results
                ],
                ensure_ascii=False,
            )

            draft = self._ask_and_parse(
                model_cls=ResearchResponse,
                user_prompt=SYNTHESIS_WITH_SEARCH_PROMPT.format(
                    question=question,
                    search_results=search_json,
                ),
                schema_hint='{"query_type":"search"}',
            )

        elif decision.need_search and not search_results:

            draft = ResearchResponse(
                query_type="search",
                summary=(
                    "No reliable external information could be found "
                    f"for '{question}'."
                ),
                key_findings=[
                    "The query was classified as requiring web search.",
                    "No reliable search results were returned.",
                    "Generating an answer from internal knowledge could be inaccurate.",
                    "The requested topic may be niche, misspelled, newly created, or insufficiently documented online.",
                ],
                recommended_next_steps=[
                    "Verify the spelling of the term.",
                    "Provide additional context about the topic.",
                    "Try a more specific query.",
                    "Search again later if the topic is very recent.",
                ],
                sources=[],
            )

        else:

            draft = self._ask_and_parse(
                model_cls=ResearchResponse,
                user_prompt=SYNTHESIS_NO_SEARCH_PROMPT.format(
                    question=question
                ),
                schema_hint='{"query_type":"no_search"}',
            )

        # # ==========================================
        # # TEMPORARY REFLECTION TEST
        # # ==========================================

        # draft = ResearchResponse(
        #     query_type="no_search",
        #     summary="Linear Regression is a neural network.",
        #     key_findings=[],
        #     recommended_next_steps=[],
        #     sources=[],
        #     )    

        # --------------------------------------------------
        # Reflection Layer
        # --------------------------------------------------

        reflection = self._ask_and_parse(
            model_cls=ReflectionReview,
            user_prompt=REFLECTION_PROMPT.format(
                question=question,
                draft_json=draft.model_dump_json(),
            ),
            schema_hint="""
            {
                "is_complete": true,
                "has_sources_when_needed": true,
                "is_educational": true,
                "should_revise": false,
                "revision_notes": []
            }
            """,
        )

        # --------------------------------------------------
        # Revision Layer
        # --------------------------------------------------

        final_response = draft

        if (
            reflection.should_revise
            and reflection.revision_notes
        ):

            final_response = self._ask_and_parse(
                model_cls=ResearchResponse,
                user_prompt=REVISION_PROMPT.format(
                    question=question,
                    revision_notes=reflection.revision_notes,
                    draft_json=draft.model_dump_json(),
                ),
                schema_hint='{"query_type":"search"}',
            )

        # --------------------------------------------------
        # Final Output
        # --------------------------------------------------

        return AgentRunOutput(
            user_query=question,
            decision=decision,
            tool_used=tool_used,
            search_results=search_results,
            response=final_response,
            reflection=reflection,
        )