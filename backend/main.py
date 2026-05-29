#!/usr/bin/env python3
"""
Learnable Backend — AI-powered knowledge tree expansion API.

Endpoints:
  POST /api/expand    →  Expand a topic into sub-topics via Kimi LLM
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

app = FastAPI(title="Learnable", version="0.1.0")

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
    depth: int = Field(1, ge=1, le=5)
    language: str = Field("zh", pattern="^(zh|en)$")


class KnowledgeNode(BaseModel):
    id: str
    label: str
    description: str = ""


class ExpandResponse(BaseModel):
    parent: str
    nodes: list[KnowledgeNode]


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

SYSTEM_ZH = """你是 Learnable 知识引擎。当用户提供一个知识点时，你需要生成 3-5 个最重要的子知识点。

要求：
1. 子知识点必须是实际可学习的、有意义的概念
2. 避免过于粗糙或过于细节
3. 每个子知识点附带一句简短描述
4. 输出格式必须是 JSON，不要任何解释

输出格式：
{
  "nodes": [
    {"id": "1", "label": "子知识点1", "description": "简短描述"},
    ...
  ]
}"""

SYSTEM_EN = """You are the Learnable knowledge engine. When given a topic, generate 3-5 important sub-topics.

Requirements:
1. Sub-topics must be meaningful, learnable concepts
2. Avoid being too broad or too granular
3. Each sub-topic includes a brief description
4. Output must be JSON only, no explanation

Output format:
{
  "nodes": [
    {"id": "1", "label": "Sub-topic 1", "description": "Brief description"},
    ...
  ]
}"""


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/expand", response_model=ExpandResponse)
async def expand_topic(req: ExpandRequest) -> ExpandResponse:
    """Expand a topic into sub-topics using Kimi LLM."""
    system = SYSTEM_ZH if req.language == "zh" else SYSTEM_EN
    prompt = f"请为以下知识点生成子知识点：{req.topic}"

    raw = kimi.chat(system, prompt, temperature=0.7)

    # Extract JSON
    try:
        data = _extract_json(raw)
        nodes = [KnowledgeNode(**n) for n in data.get("nodes", [])]
    except Exception as e:
        # Fallback: mock data
        nodes = _mock_expand(req.topic, req.language)

    return ExpandResponse(parent=req.topic, nodes=nodes)


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


def _mock_expand(topic: str, language: str) -> list[KnowledgeNode]:
    """Fallback mock data when Kimi is unavailable."""
    if language == "zh":
        return [
            KnowledgeNode(id="1", label=f"{topic} 的基础概念", description="理解核心定义和基本原理"),
            KnowledgeNode(id="2", label=f"{topic} 的应用场景", description="实际案例和使用场景分析"),
            KnowledgeNode(id="3", label=f"{topic} 的进阶技巧", description="提高效率的高级方法"),
        ]
    return [
        KnowledgeNode(id="1", label=f"Basics of {topic}", description="Core definitions and principles"),
        KnowledgeNode(id="2", label=f"Applications of {topic}", description="Real-world use cases and scenarios"),
        KnowledgeNode(id="3", label=f"Advanced {topic} techniques", description="Methods to improve efficiency"),
    ]


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
