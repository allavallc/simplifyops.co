"""Governed read-only knowledge retrieval — the first repo-owned MCP connector (story-64 Phase C2).

Exposes list/read/search over the curated knowledge store to the Hermes runtime. All authorization is
server-side: the opaque `tool_context` token (minted by the gateway) is the ONLY authority source —
authority claimed by the model is ignored. Archived and over-authority documents are filtered before
any list/read/search, and an invisible slug is indistinguishable from a missing one. The token is a
secret: it never appears in logs, results, or error messages.

Launch pattern (spec §6): `connectors.knowledge.mcp_server`, registered as an `mcp_servers` entry so
the runtime's native MCP client discovers the tools as `mcp_knowledge_*`. It reaches the shared
knowledge service and Postgres directly (env-owned DB access): `connector -> shared service -> DB`.
"""

import logging
import sys
from pathlib import Path

# The shared services (db, knowledge_store, tool_context_store) live under admin_api/.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "admin_api"))

import knowledge_store as ks  # noqa: E402
import tool_context_store as tcs  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402
from mcp.server.fastmcp.exceptions import ToolError  # noqa: E402

log = logging.getLogger("simplifyops-knowledge-connector")

mcp = FastMCP("knowledge")


def _resolve(tool_context: str) -> dict:
    """Resolve the opaque token to its trusted context, or raise. Never echoes the token."""
    if not tool_context or not tool_context.strip():
        raise ToolError("missing tool_context")
    ctx = tcs.resolve(tool_context.strip())
    if not ctx:
        raise ToolError("invalid or expired tool_context")
    return ctx


@mcp.tool()
def list_knowledge_docs(tool_context: str, category: str | None = None) -> dict:
    """List visible curated knowledge documents (summaries), optionally within one category."""
    ctx = _resolve(tool_context)
    log.info("list_knowledge_docs request_id=%s category=%s", ctx.get("request_id"), category)
    docs = ks.list_docs(folder=category, status="active", requester_authority=ctx["authority"])
    return {"status": "ok", "documents": docs}


@mcp.tool()
def read_knowledge_doc(tool_context: str, slug: str) -> dict:
    """Read one visible document (summary + `content_md`) by slug. Missing and invisible slugs return
    the same not-found error."""
    ctx = _resolve(tool_context)
    if not slug or not slug.strip():
        raise ToolError("missing slug")
    log.info("read_knowledge_doc request_id=%s slug=%s", ctx.get("request_id"), slug.strip())
    doc = ks.get_visible_by_slug(slug.strip(), ctx["authority"])
    if doc is None:
        raise ToolError("document not found")
    return {"status": "ok", "document": doc}


@mcp.tool()
def search_knowledge_docs(tool_context: str, query: str,
                          category: str | None = None, max_results: int = 20) -> dict:
    """Case-insensitive substring search over visible document bodies. `max_results` is clamped to
    1–50; each match is `{slug, title, category, line, snippet}`."""
    ctx = _resolve(tool_context)
    if not query or not query.strip():
        raise ToolError("query must be nonempty")
    q = query.strip()
    log.info("search_knowledge_docs request_id=%s category=%s q=%r", ctx.get("request_id"), category, q)
    matches = ks.search_visible(q, ctx["authority"], category=category, max_results=max_results)
    return {"status": "ok", "query": q, "matches": matches}


def main() -> None:
    # stdio transport uses stdout for the MCP protocol — logs MUST go to stderr.
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    from db import init_pool
    init_pool()
    log.info("knowledge connector starting (stdio)")
    mcp.run()


if __name__ == "__main__":
    main()
