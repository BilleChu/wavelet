"""
Chat API Routes for OpenFinance.

Provides agentic chat interface with SSE streaming.
This is a thin API layer that delegates to AgentLoop.
"""

import json
import os
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from openfinance.agents.core.loop import AgentLoop, LoopEvent, get_agent_loop
from openfinance.agents.skills.loader import SkillsLoader, BUILTIN_SKILLS_DIR
from openfinance.agents.skills.base import SkillInfo
from openfinance.agents.llm.client import get_llm_client
from openfinance.agents.session import SessionManager
from openfinance.models.base import AgentFlowRequest, AgentFlowResponse
from openfinance.core.logging_config import get_logger

from pathlib import Path

logger = get_logger(__name__)

router = APIRouter(tags=["chat"])

BACKEND_DIR = Path(__file__).parent.parent.parent
SKILLS_WORKSPACE = BACKEND_DIR / "workspace"


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")


class SkillChatRequest(BaseModel):
    """Request for skill-based chat."""
    query: str = Field(..., description="User query")
    skill_id: str | None = Field(default=None, description="Skill ID to use")
    history: list[ChatMessage] = Field(default_factory=list, description="Conversation history")
    stream: bool = Field(default=True, description="Enable streaming response")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class ChatService:
    """
    Thin wrapper for chat API.
    
    Delegates all business logic to AgentLoop.
    """
    
    _instance = None
    _session_manager: SessionManager | None = None
    _agent_loop: AgentLoop | None = None
    
    def __init__(self):
        self.skills_loader = SkillsLoader(SKILLS_WORKSPACE, BUILTIN_SKILLS_DIR)
        self._role_skill_map = {
            "warren_buffett": "buffett-investment",
            "ray_dalio": "macro-analysis",
            "catherine_wood": "tech-indicator",
        }
    
    @classmethod
    def get_instance(cls) -> "ChatService":
        """Get singleton instance of ChatService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def get_session_manager(cls) -> SessionManager:
        """Get or create session manager instance."""
        if cls._session_manager is None:
            cls._session_manager = SessionManager(workspace=SKILLS_WORKSPACE)
        return cls._session_manager
    
    @classmethod
    def get_agent_loop(cls) -> AgentLoop:
        """Get or create agent loop instance."""
        if cls._agent_loop is None:
            cls._agent_loop = AgentLoop(
                llm_client=get_llm_client(),
                workspace=SKILLS_WORKSPACE,
                session_manager=cls.get_session_manager(),
            )
        return cls._agent_loop
    
    def detect_skill(self, query: str, role: str | None = None) -> str:
        """Detect which skill to use based on query."""
        if role and role in self._role_skill_map:
            return self._role_skill_map[role]
        
        skills = self.skills_loader.list_skills(filter_unavailable=False)
        query_lower = query.lower()
        
        for skill in skills:
            if skill.metadata and skill.metadata.triggers:
                for trigger in skill.metadata.triggers:
                    if trigger.lower() in query_lower:
                        logger.info(f"Skill detected: {skill.name} (trigger: {trigger})")
                        return skill.name
        
        return "intelligent-analysis"
    
    def get_skill(self, skill_name: str) -> SkillInfo | None:
        """Get skill info by name."""
        skills = self.skills_loader.list_skills(filter_unavailable=False)
        for skill in skills:
            if skill.name == skill_name:
                return skill
        return None
    
    def build_system_prompt(self, skill_name: str, skill: SkillInfo | None) -> str:
        """Build system prompt with skill content."""
        parts = []
        
        parts.append("""# OpenFinance Agent

You are an intelligent financial assistant with access to tools that allow you to:
- Analyze financial data and investments
- Use specialized skills for complex tasks
- Provide professional investment advice

## Capabilities
- Stock analysis and valuation
- Macroeconomic analysis
- Technical indicator analysis
- Investment strategy recommendations""")
        
        if skill:
            parts.append(f"""
## Current Skill: {skill_name}

**Description:** {skill.metadata.description if skill.metadata else 'General analysis'}""")
            
            skill_content = self.skills_loader.load_skill(skill_name)
            if skill_content:
                content_without_frontmatter = self.skills_loader._strip_frontmatter(skill_content)
                parts.append(f"""
## Skill Guidelines

{content_without_frontmatter}""")
        
        parts.append("""
## Response Guidelines
1. Be professional and accurate
2. Provide actionable insights
3. Cite data sources when possible
4. Acknowledge uncertainties
5. Follow the skill's analysis framework when applicable""")
        
        return "\n".join(parts)
    
    def list_skills(self) -> list[SkillInfo]:
        """List all available skills."""
        return self.skills_loader.list_skills(filter_unavailable=False)


def get_chat_service() -> ChatService:
    """Get the chat service instance."""
    return ChatService.get_instance()


def event_to_sse(event: LoopEvent) -> str:
    """Convert a LoopEvent to SSE format."""
    data = asdict(event)
    data.pop('duration_ms', None)
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(request: AgentFlowRequest) -> AgentFlowResponse:
    """Process a chat request (non-streaming)."""
    service = get_chat_service()
    agent_loop = service.get_agent_loop()
    
    skill_name = service.detect_skill(request.query, request.role)
    skill = service.get_skill(skill_name)
    system_prompt = service.build_system_prompt(skill_name, skill)
    
    session_key = f"web:{request.user.ldap_id}"
    final_content = None
    
    async for event in agent_loop.stream_process(
        content=request.query,
        session_key=session_key,
        system_prompt=system_prompt,
    ):
        if event.type == "final":
            final_content = event.content
    
    return AgentFlowResponse(
        success=True,
        content=final_content or "No response generated",
        trace_id=f"chat_{skill_name}",
    )


@router.post("/chat/stream")
async def chat_stream(request: AgentFlowRequest):
    """Process a chat request with streaming response (SSE)."""
    service = get_chat_service()
    agent_loop = service.get_agent_loop()
    
    skill_name = service.detect_skill(request.query, request.role)
    skill = service.get_skill(skill_name)
    system_prompt = service.build_system_prompt(skill_name, skill)
    
    session_id = None
    if request.meta and request.meta.extended_info:
        session_id = request.meta.extended_info.get("session_id")
    
    session_key = f"web:{request.user.ldap_id}:{session_id}" if session_id else f"web:{request.user.ldap_id}"
    
    async def generate():
        async for event in agent_loop.stream_process(
            content=request.query,
            session_key=session_key,
            system_prompt=system_prompt,
        ):
            yield event_to_sse(event)
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/skill/{skill_id}")
async def chat_with_skill(skill_id: str, request: SkillChatRequest):
    """Chat with a specific skill agent."""
    service = get_chat_service()
    agent_loop = service.get_agent_loop()
    
    skill = service.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    
    system_prompt = service.build_system_prompt(skill_id, skill)
    session_id = request.context.get("session_id") if request.context else None
    session_key = f"web:skill:{skill_id}:{session_id}" if session_id else f"web:skill:{skill_id}"
    
    if request.stream:
        async def generate():
            async for event in agent_loop.stream_process(
                content=request.query,
                session_key=session_key,
                history=[msg.model_dump() for msg in request.history],
                system_prompt=system_prompt,
            ):
                yield event_to_sse(event)
            
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        final_content = None
        async for event in agent_loop.stream_process(
            content=request.query,
            session_key=session_key,
            history=[msg.model_dump() for msg in request.history],
            system_prompt=system_prompt,
        ):
            if event.type == "final":
                final_content = event.content
        
        return {
            "success": True,
            "content": final_content or "No response generated",
            "skill_id": skill_id,
            "trace_id": f"chat_{skill_id}",
        }


@router.get("/chat/skills")
async def list_skills() -> dict:
    """List all available skills."""
    service = get_chat_service()
    skills = service.list_skills()
    
    return {
        "skills": [
            {
                "skill_id": skill.name,
                "name": skill.name,
                "description": skill.metadata.description if skill.metadata else "",
                "triggers": skill.metadata.triggers if skill.metadata else [],
                "available": skill.available,
            }
            for skill in skills
        ]
    }


@router.get("/chat/suggestions")
async def get_chat_suggestions() -> dict:
    """Get suggested questions for chat."""
    return {
        "suggestions": [
            "用巴菲特的投资理念分析贵州茅台",
            "达里奥会如何配置我的投资组合？",
            "凯瑟琳·伍德看好哪些创新领域？",
            "如何评估一家公司的护城河？",
            "当前市场环境下应该采取什么策略？",
            "如何构建一个抗风险的投资组合？",
        ]
    }
