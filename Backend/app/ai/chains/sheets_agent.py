from __future__ import annotations

import pandas as pd
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent

from app.ai.llm import llm

_SYSTEM_PREFIX = """You are a data analyst assistant. You have access to a pandas DataFrame called `df`.

RULES:
1. Always answer from the provided DataFrame ONLY.
2. When asked for specific data, ALWAYS include the actual values/numbers in your response.
3. If a query returns multiple rows, format them as a readable list or table.
4. Never say "The details are:" without actually listing the details.
5. If you run a pandas operation and get results, include those results in your final answer.
6. Use df.to_string() or df.to_markdown() when you need to show tabular data.
7. If you cannot find the data, say so clearly.
8. Be thorough - show all relevant columns and values."""


def run_dataframe_agent(df: pd.DataFrame, question: str, user_email: str) -> str:
    """Create a Pandas DataFrame agent and run a question against it."""

    # Provide column info in the question for better context
    col_info = f"\n\nDataFrame columns: {list(df.columns)}\nTotal rows: {len(df)}\nSample (first 3 rows):\n{df.head(3).to_string()}"
    enriched_question = question + col_info

    agent = create_pandas_dataframe_agent(
        llm,
        df,
        agent_type="openai-tools",
        allow_dangerous_code=True,
        verbose=True,
        max_iterations=15,
        handle_parsing_errors=True,
        prefix=_SYSTEM_PREFIX,
        return_intermediate_steps=True,
        number_of_head_rows=5,
    )

    result = agent.invoke(
        {"input": enriched_question},
        config={"metadata": {"user_email": user_email}},
    )

    output = result.get("output", "")

    # If output is empty or too short, try to extract from intermediate steps
    if not output or len(output.strip()) < 10:
        steps = result.get("intermediate_steps", [])
        if steps:
            last_step = steps[-1]
            if isinstance(last_step, tuple) and len(last_step) > 1:
                observation = str(last_step[1])
                if observation and len(observation) > 10:
                    return observation

        return "I could not generate a complete answer from the data. Please try rephrasing your question."

    return output
