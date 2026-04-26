"""
Aphrodite Supervisor — FastMCP: Web-Search ve RAG pod'larına HTTP köprüsü + sağlık özeti.

Çalıştırma (stdio, MCP Inspector / interactive_chat):
  cd MCP-Workplace && python -m aphrodite_mcp.server
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from aphrodite_mcp.settings import gateway_url, llm_pod_url, rag_pod_url, web_search_pod_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aphrodite-mcp-server")

mcp = FastMCP(
    "Aphrodite Supervisor",
    instructions=(
        "Aphrodite pod araçları: web araması, moda RAG katalog araması ve servis sağlık özeti. "
        "Araçlar mevcut FastAPI pod'larına HTTP ile bağlanır."
    ),
)


def _format_web_results(data: dict[str, Any]) -> str:
    lines = [
        f"query: {data.get('query', '')}",
        f"total: {data.get('total_results', 0)} cached: {data.get('cached')} time: {data.get('processing_time')}",
        "",
    ]
    for i, r in enumerate(data.get("results") or [], 1):
        lines.append(f"[{i}] {r.get('title', '')}")
        lines.append(f"    url: {r.get('url', '')}")
        lines.append(f"    {r.get('snippet', '')[:400]}")
        lines.append("")
    return "\n".join(lines).strip()


def _format_rag_results(data: dict[str, Any]) -> str:
    lines = [
        f"query: {data.get('query', '')}",
        f"total: {data.get('total_results', 0)} cached: {data.get('cached')} time: {data.get('processing_time')}",
        "",
    ]
    for i, r in enumerate(data.get("results") or [], 1):
        p = r.get("product") or {}
        score = r.get("similarity_score", "")
        lines.append(f"[{i}] score={score} {p.get('name', '')} ({p.get('category', '')})")
        desc = (p.get("description") or "")[:300]
        if desc:
            lines.append(f"    {desc}")
        lines.append("")
    return "\n".join(lines).strip()


@mcp.tool()
async def web_search(
    query: str,
    max_results: int = 5,
    language: str = "tr",
    region: str = "tr",
) -> str:
    """İnternette arama yapar (Web-Search Pod)."""
    url = f"{web_search_pod_url()}/search"
    payload = {
        "query": query,
        "max_results": max_results,
        "language": language,
        "region": region,
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        return _format_web_results(data)
    except Exception as e:
        logger.exception("web_search")
        return f"[hata] web_search: {e!s}"


@mcp.tool()
async def rag_fashion_search(
    query: str,
    max_results: int = 10,
    similarity_threshold: float = 0.65,
    category: str | None = None,
    brand: str | None = None,
) -> str:
    """Moda katalog / vektör araması (RAG Pod)."""
    url = f"{rag_pod_url()}/search"
    payload: dict[str, Any] = {
        "query": query,
        "max_results": max_results,
        "similarity_threshold": similarity_threshold,
    }
    if category:
        payload["category"] = category
    if brand:
        payload["brand"] = brand
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        return _format_rag_results(data)
    except Exception as e:
        logger.exception("rag_fashion_search")
        return f"[hata] rag_fashion_search: {e!s}"


@mcp.tool()
async def aphrodite_pods_health() -> str:
    """Web-Search, RAG, LLM ve isteğe bağlı Gateway için /health özetini döndürür."""
    targets = [
        ("web_search", f"{web_search_pod_url()}/health"),
        ("rag", f"{rag_pod_url()}/health"),
        ("llm", f"{llm_pod_url()}/health"),
        ("gateway", f"{gateway_url()}/health"),
    ]
    lines: list[str] = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, href in targets:
            try:
                r = await client.get(href)
                lines.append(f"{name}: HTTP {r.status_code}")
                if r.status_code == 200:
                    try:
                        body = r.json()
                        lines.append(f"  {json.dumps(body, ensure_ascii=False)[:500]}")
                    except Exception:
                        lines.append(f"  {r.text[:200]}")
            except Exception as e:
                lines.append(f"{name}: [hata] {e!s}")
            lines.append("")
    return "\n".join(lines).strip()


@mcp.resource("resource://aphrodite/supervisor")
async def supervisor_manifest() -> str:
    """Bağlı pod URL'leri ve araç listesi özeti (denetim / dokümantasyon)."""
    meta = {
        "web_search_pod": web_search_pod_url(),
        "rag_pod": rag_pod_url(),
        "llm_pod": llm_pod_url(),
        "gateway": gateway_url(),
        "tools": ["web_search", "rag_fashion_search", "aphrodite_pods_health"],
    }
    return json.dumps(meta, indent=2, ensure_ascii=False)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
