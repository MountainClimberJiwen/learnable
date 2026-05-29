#!/usr/bin/env python3
"""
Learnable Backend — AI-powered knowledge tree expansion API.

Endpoints:
  POST /api/expand    →  Expand a topic into sub-topic labels (list only)
  POST /api/detail    →  Get detailed content for a single sub-topic
  GET  /api/health    →  Health check
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load API key from agentrl .env
env_path = Path("/opt/agentrl/.env")
if env_path.exists():
    load_dotenv(env_path)

KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "")
KIMI_BASE_URL = os.environ.get("KIMI_BASE_URL", "https://api.moonshot.cn/v1")

app = FastAPI(title="Learnable", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ExpandRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    language: str = Field("zh", pattern="^(zh|en)$")


class ExpandResponse(BaseModel):
    parent: str
    items: list[dict]


class DetailRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    parent: str = Field("", max_length=200)
    language: str = Field("zh", pattern="^(zh|en)$")


class DetailResponse(BaseModel):
    topic: str
    parent: str
    definition: str
    key_points: list[str]
    example: str


# ---------------------------------------------------------------------------
# Kimi Client
# ---------------------------------------------------------------------------

class KimiClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or KIMI_API_KEY
        self.base_url = KIMI_BASE_URL
        self.model = "moonshot-v1-8k"

    def chat(self, system: str, user: str, temperature: float = 0.7) -> str:
        if not self.api_key:
            raise RuntimeError("KIMI_API_KEY not configured")

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "learnable-backend",
            },
            data=json.dumps({
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
            }, ensure_ascii=False).encode("utf-8"),
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]


kimi = KimiClient()


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

EXPAND_SYSTEM_ZH = """你是 Learnable 知识引擎。当用户提供一个知识点时，仅仅返回 3-5 个最重要的子知识点名称，不要任何描述或解释。

要求：
1. 子知识点必须是有意义的、可学习的概念
2. 每个名称简洁，不超过 10 个字
3. 输出格式必须是 JSON，不要任何解释

输出格式：
{
  "items": [
    {"id": "1", "label": "子知识点1"},
    {"id": "2", "label": "子知识点2"},
    ...
  ]
}"""

EXPAND_SYSTEM_EN = """You are the Learnable knowledge engine. When given a topic, return only 3-5 important sub-topic names. No descriptions.

Requirements:
1. Sub-topics must be meaningful, learnable concepts
2. Each name is concise, under 6 words
3. Output must be JSON only, no explanation

Output format:
{
  "items": [
    {"id": "1", "label": "Sub-topic 1"},
    {"id": "2", "label": "Sub-topic 2"},
    ...
  ]
}"""

DETAIL_SYSTEM_ZH = """你是 Learnable 知识引擎。用户想了解一个具体知识点的详情。

请提供：
1. 一句话定义
2. 3-5 个核心要点
3. 一个实际应用例子

输出格式必须是 JSON：
{
  "definition": "...",
  "key_points": ["...", "..."],
  "example": "..."
}"""

DETAIL_SYSTEM_EN = """You are the Learnable knowledge engine. The user wants details on a specific topic.

Provide:
1. A one-sentence definition
2. 3-5 key points
3. A real-world application example

Output must be JSON:
{
  "definition": "...",
  "key_points": ["...", "..."],
  "example": "..."
}"""


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/expand", response_model=ExpandResponse)
async def expand_topic(req: ExpandRequest) -> ExpandResponse:
    """Expand a topic into sub-topic labels (lightweight, single LLM call)."""
    system = EXPAND_SYSTEM_ZH if req.language == "zh" else EXPAND_SYSTEM_EN
    prompt = f"主题：{req.topic}\n\n请返回这个主题的 3-5 个重要子知识点名称。"

    raw = kimi.chat(system, prompt, temperature=0.7)

    try:
        data = _extract_json(raw)
        items = data.get("items", [])
    except Exception:
        items = _mock_items(req.topic, req.language)

    return ExpandResponse(parent=req.topic, items=items)


@app.post("/api/detail", response_model=DetailResponse)
async def detail_topic(req: DetailRequest) -> DetailResponse:
    """Get detailed content for a single topic (concurrent-friendly)."""
    system = DETAIL_SYSTEM_ZH if req.language == "zh" else DETAIL_SYSTEM_EN
    prompt = f"知识点：{req.topic}\n属于领域：{req.parent or '未分类'}\n\n请提供该知识点的详细说明。"

    raw = kimi.chat(system, prompt, temperature=0.5)

    try:
        data = _extract_json(raw)
    except Exception:
        data = _mock_detail(req.topic, req.language)

    return DetailResponse(
        topic=req.topic,
        parent=req.parent,
        definition=data.get("definition", ""),
        key_points=data.get("key_points", []),
        example=data.get("example", ""),
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "kimi_configured": str(bool(KIMI_API_KEY))}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict:
    """Extract JSON from markdown code block or raw text."""
    import re
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start:end + 1])
    raise ValueError("No JSON found")


def _mock_items(topic: str, language: str) -> list[dict]:
    if language == "zh":
        return [
            {"id": "1", "label": f"{topic} 基础"},
            {"id": "2", "label": f"{topic} 应用"},
            {"id": "3", "label": f"{topic} 进阶"},
        ]
    return [
        {"id": "1", "label": f"{topic} Basics"},
        {"id": "2", "label": f"{topic} Applications"},
        {"id": "3", "label": f"{topic} Advanced"},
    ]


def _mock_detail(topic: str, language: str) -> dict:
    if language == "zh":
        return {
            "definition": f"{topic}是一个重要的知识领域，涉及多个核心概念和实践应用。",
            "key_points": ["核心原理", "关键技术", "实际应用", "发展趋势"],
            "example": f"例如，在实际项目中运用{topic}解决了复杂问题。",
        }
    return {
        "definition": f"{topic} is an important knowledge domain involving multiple core concepts and practical applications.",
        "key_points": ["Core principles", "Key techniques", "Real-world usage", "Future trends"],
        "example": f"For example, applying {topic} in real projects solved complex problems.",
    }


# ---------------------------------------------------------------------------
# Static files (frontend)
# ---------------------------------------------------------------------------

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_path = Path(__file__).parent.parent / "frontend"
if (frontend_path / "index.html").exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/")
    async def serve_index() -> FileResponse:
        return FileResponse(str(frontend_path / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
