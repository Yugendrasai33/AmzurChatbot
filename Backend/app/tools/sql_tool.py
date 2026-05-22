"""SQL query tool — wraps generate_sql + execute_sql_structured from sql_chain."""
from __future__ import annotations

from typing import Any


async def execute_sql_query(question: str, user_email: str = "system") -> dict[str, Any]:
    """Generate SQL from a question and execute it.

    Returns:
        dict with keys: success, sql_query, columns, rows, row_count
    """
    if not question or not question.strip():
        return {"success": False, "error": "Question cannot be empty"}

    try:
        from app.ai.chains.sql_chain import execute_sql_structured, generate_sql

        # generate_sql requires chat history — pass empty for direct tool call
        sql_query = await generate_sql(question.strip(), [], user_email)

        # Execute the validated SQL
        structured = execute_sql_structured(sql_query)

        return {
            "success": True,
            "sql_query": sql_query,
            "columns": structured["columns"],
            "rows": structured["rows"][:100],  # Limit rows to prevent huge payloads
            "row_count": len(structured["rows"]),
        }
    except ValueError as e:
        # Safety validation rejected the query
        return {
            "success": False,
            "error": f"Query rejected: {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"SQL query failed: {e}",
        }
