from __future__ import annotations

from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough

from app.ai.chains.sql_safety import ALLOWED_TABLES, validate_sql
from app.ai.chains.sql_utils import _build_sync_db_url
from app.ai.llm import llm

# ---------------------------------------------------------------------------
# Lazy-initialised SQLDatabase (created on first use so import-time errors
# don't block the rest of the app when DATABASE_URL is absent).
# ---------------------------------------------------------------------------

_sql_db: SQLDatabase | None = None


def _get_sql_db() -> SQLDatabase:
    global _sql_db
    if _sql_db is None:
        _sql_db = SQLDatabase.from_uri(
            _build_sync_db_url(),
            include_tables=ALLOWED_TABLES,
        )
    return _sql_db


# ---------------------------------------------------------------------------
# Step 1 — Natural language → SQL
# ---------------------------------------------------------------------------

_sql_gen_system = (
    "You are a PostgreSQL expert. Given the database schema below, write a single "
    "SELECT query that answers the user's question.\n\n"
    "RULES:\n"
    "- Output ONLY the raw SQL query, nothing else — no markdown, no explanation.\n"
    "- NEVER use INSERT, UPDATE, DELETE, DROP, TRUNCATE, or ALTER.\n"
    "- Use only these tables: {allowed_tables}\n\n"
    "Schema:\n{schema}"
)

_sql_gen_prompt = ChatPromptTemplate.from_messages([
    ("system", _sql_gen_system),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
])


def _get_schema(_input: dict) -> dict:
    """Inject the DB schema and allowed tables into the prompt variables."""
    db = _get_sql_db()
    return {
        **_input,
        "schema": db.get_table_info(),
        "allowed_tables": ", ".join(ALLOWED_TABLES),
    }


_sql_gen_chain = (
    RunnablePassthrough.assign(**{k: lambda _: None for k in []})  # passthrough
    | _get_schema
    | _sql_gen_prompt
    | llm
    | StrOutputParser()
)

# ---------------------------------------------------------------------------
# Step 2 — SQL result → natural-language answer
# ---------------------------------------------------------------------------

_answer_system = (
    "You are a helpful data assistant. A SQL query was run to answer the user's question.\n\n"
    "IMPORTANT RULES — follow strictly:\n"
    "1. Reply with ONLY a brief, friendly summary in 1-2 sentences.\n"
    "2. NEVER list, quote, or repeat any raw data such as IDs, UUIDs, timestamps, \n"
    "   dates, column values, or row content. The user already sees a data table.\n"
    "3. Just state the high-level finding, e.g. 'Found 8 chat threads' or \n"
    "   'There are 3 users in the database'.\n"
    "4. If no rows were returned, say 'No matching results were found.'\n"
    "5. Keep it conversational and simple — no bullet points, no lists, no tables.\n\n"
    "Context (for your understanding only — do NOT expose any of this):\n"
    "SQL: {sql_query}\n"
    "Rows returned: {row_count}\n"
    "Columns: {column_names}\n"
    "Sample data: {sql_result}"
)

_answer_prompt = ChatPromptTemplate.from_messages([
    ("system", _answer_system),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
])

_answer_chain = _answer_prompt | llm | StrOutputParser()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_sql(question: str, history: list, user_email: str) -> str:
    """Generate a validated SQL query from a natural-language question."""
    raw_sql: str = await _sql_gen_chain.ainvoke(
        {"question": question, "history": history},
        config={"metadata": {"user_email": user_email}},
    )
    # Strip markdown fences the LLM might wrap the query in
    cleaned = raw_sql.strip().strip("`").strip()
    if cleaned.lower().startswith("sql"):
        cleaned = cleaned[3:].strip()
    return validate_sql(cleaned)


def execute_sql(sql: str) -> str:
    """Execute a read-only SQL query and return the result as a string."""
    db = _get_sql_db()
    return db.run(sql)


def execute_sql_structured(sql: str) -> dict:
    """Execute a read-only SQL query and return columns + rows for table display.

    Returns ``{"columns": [...], "rows": [[...], ...], "result_str": "..."}``
    """
    from sqlalchemy import create_engine, text as sa_text

    engine = create_engine(_build_sync_db_url())
    with engine.connect() as conn:
        result = conn.execute(sa_text(sql))
        columns = list(result.keys())
        rows = [list(str(v) if v is not None else "" for v in row) for row in result.fetchall()]

    return {
        "columns": columns,
        "rows": rows,
        "result_str": str(rows),
    }


async def answer_from_result(
    question: str,
    sql_query: str,
    sql_result: str,
    history: list,
    user_email: str,
    row_count: int = 0,
    column_names: str = "",
) -> str:
    """Generate a natural-language answer from SQL results (non-streaming)."""
    return await _answer_chain.ainvoke(
        {
            "question": question,
            "sql_query": sql_query,
            "sql_result": sql_result,
            "history": history,
            "row_count": str(row_count),
            "column_names": column_names,
        },
        config={"metadata": {"user_email": user_email}},
    )


async def stream_answer_from_result(
    question: str,
    sql_query: str,
    sql_result: str,
    history: list,
    user_email: str,
    row_count: int = 0,
    column_names: str = "",
):
    """Stream a natural-language answer from SQL results token-by-token."""
    async for token in _answer_chain.astream(
        {
            "question": question,
            "sql_query": sql_query,
            "sql_result": sql_result,
            "history": history,
            "row_count": str(row_count),
            "column_names": column_names,
        },
        config={"metadata": {"user_email": user_email}},
    ):
        yield token
