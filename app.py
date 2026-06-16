import time

import streamlit as st

from config import settings
from agent import LLMClient, ResearchScoutAgent
from tools import TavilySearchTool


# ==================================================
# Page Configuration
# ==================================================

st.set_page_config(
    page_title="ResearchScout AI",
    page_icon="🔍",
    layout="wide",
)

# ==================================================
# Sidebar
# ==================================================

with st.sidebar:

    st.title("🔍 ResearchScout AI")

    st.markdown(
        """
        ### Agent Workflow

        Observe  
        ↓  
        Reason  
        ↓  
        Decide  
        ↓  
        Act  
        ↓  
        Reflect  
        ↓  
        Respond
        """
    )

    st.divider()

    st.markdown("### Configuration")

    provider = getattr(settings, "llm_provider", "deepseek")

    st.write(f"**LLM Provider:** {provider}")
    st.write("**Search Tool:** Tavily")

    st.divider()

    st.markdown(
        """
        ### Example Queries

        - What is Gradient Descent?
        - Compare BERT and GPT
        - Latest developments in Agentic AI
        - Most in-demand AI skills in 2026
        - Explain Reinforcement Learning
        """
    )

# ==================================================
# Title Section
# ==================================================

st.title("🔍 ResearchScout AI")

st.caption(
    "Agentic Learning & Research Assistant for AI/ML Students"
)

st.info(
    "ResearchScout follows a multi-stage agent workflow: "
    "Decision → Search → Synthesis → Reflection → Response"
)

# ==================================================
# Agent Loader
# ==================================================

@st.cache_resource
def load_agent():

    llm = LLMClient()

    search_tool = TavilySearchTool(
        api_key=settings.tavily_api_key
    )

    return ResearchScoutAgent(
        llm=llm,
        search_tool=search_tool,
    )


agent = load_agent()

# ==================================================
# Query Input
# ==================================================

query = st.text_area(
    "Enter your research question",
    placeholder="Example: Latest developments in Agentic AI",
    height=120,
)

ask_button = st.button(
    "Ask ResearchScout",
    use_container_width=True,
)

# ==================================================
# Main Execution
# ==================================================

if ask_button:

    if not query.strip():
        st.warning("Please enter a question.")
        st.stop()

    try:

        start_time = time.time()

        with st.spinner("ResearchScout is thinking..."):

            result = agent.run(query)

        elapsed = round(
            time.time() - start_time,
            2
        )

        st.caption(
            f"⏱ Response generated in {elapsed} seconds"
        )

        # ==========================================
        # Agent Decision
        # ==========================================

        st.divider()

        st.subheader("🧠 Agent Decision")

        if result.decision.need_search:

            st.success(
                "🔎 External Search Required"
            )

        else:

            st.info(
                "🧠 Internal Knowledge Sufficient"
            )

        st.write("### Reason")

        st.write(
            result.decision.reason
        )

        st.write(
            f"**Tool Used:** `{result.tool_used}`"
        )

        # ==========================================
        # Tabs
        # ==========================================

        tab1, tab2, tab3, tab4 = st.tabs(
            [
                "📖 Summary",
                "🔑 Findings",
                "📚 Sources",
                "🪞 Reflection",
            ]
        )

        # ==========================================
        # Summary Tab
        # ==========================================

        with tab1:

            st.subheader("Summary")

            st.write(
                result.response.summary
            )

            st.subheader(
                "Recommended Next Steps"
            )

            for step in result.response.recommended_next_steps:

                st.markdown(
                    f"- {step}"
                )

        # ==========================================
        # Findings Tab
        # ==========================================

        with tab2:

            st.subheader(
                "Key Findings"
            )

            for finding in result.response.key_findings:

                st.markdown(
                    f"- {finding}"
                )

        # ==========================================
        # Sources Tab
        # ==========================================

        with tab3:

            if result.response.sources:

                st.subheader(
                    "Sources"
                )

                for source in result.response.sources:

                    st.link_button(
                        source.title,
                        source.url,
                        use_container_width=True,
                    )

            else:

                st.info(
                    "No external sources were required."
                )

        # ==========================================
        # Reflection Tab
        # ==========================================

        with tab4:

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Complete",
                    "Yes"
                    if result.reflection.is_complete
                    else "No"
                )

            with col2:

                st.metric(
                    "Educational",
                    "Yes"
                    if result.reflection.is_educational
                    else "No"
                )

            with col3:

                st.metric(
                    "Revision Needed",
                    "Yes"
                    if result.reflection.should_revise
                    else "No"
                )

            if result.reflection.revision_notes:

                st.subheader(
                    "Revision Notes"
                )

                for note in result.reflection.revision_notes:

                    st.markdown(
                        f"- {note}"
                    )

        # ==========================================
        # Raw Output
        # ==========================================

        with st.expander(
            "🔧 Raw Agent Output"
        ):

            st.json(
                result.model_dump()
            )

    except Exception as e:

        st.error(
            f"Agent Error: {str(e)}"
        )