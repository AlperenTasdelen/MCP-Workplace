"""Ortam: MCP-Workplace/.env ve proje kökü .env (üzerine yazmadan)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_MCP_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _MCP_ROOT.parent

for _p in (_MCP_ROOT / ".env", _PROJECT_ROOT / ".env"):
    load_dotenv(dotenv_path=_p, override=False)


def web_search_pod_url() -> str:
    return os.getenv("WEB_SEARCH_POD_URL", "http://localhost:8003").rstrip("/")


def rag_pod_url() -> str:
    return os.getenv("RAG_POD_URL", "http://localhost:8004").rstrip("/")


def llm_pod_url() -> str:
    return os.getenv("LLM_POD_URL", "http://localhost:8012").rstrip("/")


def gateway_url() -> str:
    return os.getenv("GATEWAY_URL", "http://localhost:8000").rstrip("/")


def camera_pod_url() -> str:
    return os.getenv("CAMERA_POD_URL", "http://localhost:8006").rstrip("/")


def vision_service_url() -> str:
    return os.getenv("VISION_SERVICE_POD_URL", "http://localhost:8007").rstrip("/")
