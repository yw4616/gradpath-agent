import json
import os
import re
import uuid
from pathlib import Path

import litellm
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from tools import TOOLS, run_tool, PROGRAM_DATABASE


# Config

SYSTEM_PROMPT = (
    "You are GradPath, an academic planning assistant for Columbia students. "
    "You help students reason about GPA goals, program requirements, "
    "degree progress, and course information. "

    "When an exact GPA calculation is required, always use "
    "calculate_gpa_path rather than doing the arithmetic yourself. "

    "When the user asks about the requirements of a supported Columbia "
    "graduate program, use lookup_program_requirements. "

    "When the user asks what degree requirements they personally still need, "
    "use audit_degree_requirements when their program, completed courses, "
    "and completed credits are known. "

    "Never infer a student's program solely from their course list. "
    "Only use a program when the user explicitly states it. "

    "If required information is missing, ask a concise follow-up question "
    "instead of inventing values. "

    "When a user asks about a specific Columbia course, use "
    "lookup_course_catalog. "

    "The program and course lookup tools contact official Columbia public "
    "pages. Treat tool results as reference data, but remind users that "
    "official departmental guidance is authoritative and requirements can change. "

    "Use tool results as the source of truth. "

    "Remember information the user shared earlier in the same session "
    "and reuse it when relevant."
)

MAX_TOOL_ROUNDS = 5


# Explicit Program Detection

def detect_explicit_program(text: str) -> str | None:
    """Detect a supported program only when explicitly mentioned."""

    text_lower = text.lower()

    for canonical_name, data in PROGRAM_DATABASE.items():

        possible_names = [
            canonical_name,
            *data.get("aliases", []),
        ]

        for name in possible_names:

            name_lower = name.lower().strip()

            if len(name_lower) <= 3:
                pattern = rf"\b{re.escape(name_lower)}\b"

                if re.search(pattern, text_lower):
                    return canonical_name

            elif name_lower in text_lower:
                return canonical_name

    return None


# Agent Harness

def run_agent(
    messages: list[dict],
    known_program: str | None,
) -> tuple[str, list[dict]]:

    tool_calls = []

    for _ in range(MAX_TOOL_ROUNDS):

        if known_program:
            program_context = {
                "role": "system",
                "content": (
                    f"The user's explicitly confirmed program is "
                    f"{known_program}. Use this exact program for "
                    "degree-related tools."
                ),
            }

        else:
            program_context = {
                "role": "system",
                "content": (
                    "The user has not explicitly provided a supported "
                    "graduate program. Do not infer one from course names."
                ),
            }

        model_messages = messages + [program_context]

        reply = litellm.completion(
            model="vertex_ai/gemini-3.5-flash-lite",
            vertex_location="global",
            messages=model_messages,
            tools=TOOLS,
        ).choices[0].message

        messages.append(
            reply.model_dump()
        )

        if not reply.tool_calls:
            return reply.content or "", tool_calls

        for call in reply.tool_calls:

            try:
                args = json.loads(
                    call.function.arguments
                )

            except json.JSONDecodeError:
                args = {}

            tool_name = call.function.name

            degree_tools = {
                "lookup_program_requirements",
                "audit_degree_requirements",
            }

            if tool_name in degree_tools:

                if known_program is None:
                    result = json.dumps({
                        "error": (
                            "Degree tool blocked because the user "
                            "has not explicitly provided their program."
                        )
                    })

                else:
                    args["program_name"] = known_program

                    result = run_tool(
                        tool_name,
                        args,
                    )

            else:
                result = run_tool(
                    tool_name,
                    args,
                )

            tool_calls.append({
                "name": tool_name,
                "args": args,
                "result": result,
            })

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result,
            })

    return (
        "Sorry, I reached the maximum tool-call limit.",
        tool_calls,
    )


# Session Store

sessions: dict[str, list[dict]] = {}

session_programs: dict[str, str] = {}


# FastAPI

app = FastAPI(
    title="GradPath",
    description="Columbia academic planning agent",
)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: list[dict]


# Routes

@app.get("/")
def index():
    return FileResponse(
        Path(__file__).parent / "index.html"
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    session_id = (
        request.session_id
        or str(uuid.uuid4())
    )

    if session_id not in sessions:

        sessions[session_id] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

    detected_program = detect_explicit_program(
        request.message
    )

    if detected_program:
        session_programs[session_id] = detected_program

    known_program = session_programs.get(
        session_id
    )

    sessions[session_id].append({
        "role": "user",
        "content": request.message,
    })

    try:

        response, tool_calls = run_agent(
            sessions[session_id],
            known_program,
        )

    except Exception as e:

        response = (
            "Model call failed: "
            f"{type(e).__name__}: "
            f"{str(e)[:300]}"
        )

        tool_calls = []

    return ChatResponse(
        response=response,
        session_id=session_id,
        tool_calls=tool_calls,
    )


@app.post("/clear")
def clear(session_id: str | None = None):

    if session_id:

        sessions.pop(
            session_id,
            None,
        )

        session_programs.pop(
            session_id,
            None,
        )

    return {
        "status": "ok"
    }


# Local + Cloud Run Startup

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            8000,
        )
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
    )