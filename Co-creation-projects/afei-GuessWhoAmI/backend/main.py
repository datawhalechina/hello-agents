#!/usr/bin/env python3
"""
GuessWhoAmI Game - FastAPI backend main file
Provides RESTful API for frontend
"""

import uuid
import logging
from typing import Dict
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from game_logic import GameSession
from agents import HistoricalFigureAgent
from config import get_config
from models import (
    ChatRequest, GuessRequest, StartRequest,
    HintRequest, EndRequest, GameResponse,
)

# Initialize config
config = get_config()

# Configure logging
import os as _os
_LOG_PATH = _os.path.normpath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "logs", "backend.log"))
_os.makedirs(_os.path.dirname(_LOG_PATH), exist_ok=True)

_log_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# File handler — Python owns the fd, so truncation is safe
_file_handler = logging.FileHandler(_LOG_PATH, mode="a", encoding="utf-8")
_file_handler.setFormatter(_log_formatter)

# Use addHandler directly instead of basicConfig (basicConfig is a no-op if root logger
# already has handlers, e.g. when uvicorn pre-configures logging before our code runs)
_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
_root_logger.addHandler(_file_handler)

logger = logging.getLogger("game.main")


def _clear_log_file() -> None:
    """Clear the log file by truncating it and reopening our own FileHandler."""
    # Only operate on our own _file_handler, leave uvicorn/other handlers untouched
    _file_handler.acquire()
    try:
        if _file_handler.stream is not None:
            _file_handler.stream.close()
            _file_handler.stream = None
    finally:
        _file_handler.release()
    # Truncate the file
    with open(_LOG_PATH, "w", encoding="utf-8") as f:
        pass
    # Reopen our handler in append mode
    _file_handler.acquire()
    try:
        _file_handler.stream = open(_LOG_PATH, "a", encoding="utf-8")
    finally:
        _file_handler.release()

# Create FastAPI app
app = FastAPI(
    title="猜猜我是谁游戏API",
    description="基于hello_agents框架的GuessWhoAmI游戏后端API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global session storage: session_id -> (GameSession, HistoricalFigureAgent)
active_sessions: Dict[str, tuple] = {}

# Helper functions
def get_session_pair(session_id: str):
    """Get game session and agent, raise exception if not found"""
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或已过期"
        )
    return active_sessions[session_id]

def create_response(success: bool, message: str, data: dict = None, error: str = None) -> GameResponse:
    """Create standardized response"""
    return GameResponse(
        success=success,
        message=message,
        data=data,
        error=error
    )

# API endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "猜猜我是谁游戏API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.post("/api/game/start", response_model=GameResponse)
async def start_game(request: StartRequest):
    """Start a new game"""
    try:
        # Clear log file via FileHandler to avoid NUL bytes
        _clear_log_file()
        logger.info("[START] Log file cleared")

        session_id = str(uuid.uuid4())
        # GameSession auto-initializes and picks a random figure
        game_session = GameSession()
        # Create Agent with the game session
        agent = HistoricalFigureAgent(game_session)

        # Store session and agent together
        active_sessions[session_id] = (game_session, agent)

        figure_name = game_session.current_figure.get("name", "未知")
        logger.info(f"[START] session_id={session_id} | figure={figure_name} | max_questions={game_session.max_questions} | max_hints={game_session.max_hints}")

        welcome_message = (
            f"游戏开始！我是一个知名人物，请通过提问来猜测我是谁。\n"
            f"你最多可以提问 {game_session.max_questions} 次，使用 {game_session.max_hints} 次提示。\n"
            f"开始吧！"
        )

        return create_response(
            success=True,
            message="游戏开始成功",
            data={
                "session_id": session_id,
                "welcome_message": welcome_message,
                "max_questions": game_session.max_questions,
                "max_hints": game_session.max_hints
            }
        )
    except Exception as e:
        logger.error(f"[START] 游戏启动失败: {e}", exc_info=True)
        return create_response(
            success=False,
            message="游戏启动失败",
            error=str(e)
        )

@app.post("/api/game/chat", response_model=GameResponse)
async def chat_with_agent(request: ChatRequest):
    """Chat with Agent"""
    try:
        game_session, agent = get_session_pair(request.session_id)

        # Check game state
        if game_session.is_game_over:
            logger.warning(f"[CHAT] session_id={request.session_id} | 游戏已结束，拒绝消息")
            return create_response(
                success=False,
                message="游戏已结束",
                error="请开始新游戏"
            )

        logger.info(f"[CHAT] session_id={request.session_id} | questions_asked={game_session.questions_asked} | user={request.message!r}")

        # Process message via agent
        response_message = agent.chat(request.message)

        logger.info(f"[CHAT] session_id={request.session_id} | remaining={game_session.max_questions - game_session.questions_asked} | agent={response_message!r}")

        return create_response(
            success=True,
            message="消息处理成功",
            data={
                "response": response_message,
                "remaining_questions": game_session.max_questions - game_session.questions_asked,
                "used_hints": game_session.hints_used,
                "is_game_over": game_session.is_game_over
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CHAT] session_id={request.session_id} | 消息处理失败: {e}", exc_info=True)
        return create_response(
            success=False,
            message="消息处理失败",
            error=str(e)
        )

@app.post("/api/game/guess", response_model=GameResponse)
async def guess_figure(request: GuessRequest):
    """Guess the historical figure"""
    try:
        game_session, agent = get_session_pair(request.session_id)

        # Check game state
        if game_session.is_game_over:
            logger.warning(f"[GUESS] session_id={request.session_id} | 游戏已结束，拒绝猜测")
            return create_response(
                success=False,
                message="游戏已结束",
                error="请开始新游戏"
            )

        actual_name = game_session.current_figure.get("name", "未知")
        logger.info(f"[GUESS] session_id={request.session_id} | guess={request.guess!r} | actual={actual_name!r}")

        # Make guess (agent handles semantic matching via its LLM)
        result = agent.make_guess(request.guess)

        if result["correct"]:
            logger.info(f"[GUESS] session_id={request.session_id} | 猜测正确！figure={actual_name}")
        else:
            logger.info(f"[GUESS] session_id={request.session_id} | 猜测错误 | is_game_over={game_session.is_game_over}")

        return create_response(
            success=True,
            message="猜测完成",
            data={
                "is_correct": result["correct"],
                "message": result["message"],
                "remaining_questions": game_session.max_questions - game_session.questions_asked,
                "is_game_over": game_session.is_game_over,
                "figure_info": result.get("figure_info"),
                "portrait_images": result.get("portrait_images", []),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GUESS] session_id={request.session_id} | 猜测失败: {e}", exc_info=True)
        return create_response(
            success=False,
            message="猜测失败",
            error=str(e)
        )

@app.post("/api/game/hint", response_model=GameResponse)
async def get_hint(request: HintRequest):
    """Get a hint"""
    try:
        game_session, agent = get_session_pair(request.session_id)

        # Check game state
        if game_session.is_game_over:
            logger.warning(f"[HINT] session_id={request.session_id} | 游戏已结束，拒绝提示")
            return create_response(
                success=False,
                message="游戏已结束",
                error="请开始新游戏"
            )

        # Get hint
        hint_info = game_session.get_hint()

        if hint_info.get("available"):
            logger.info(f"[HINT] session_id={request.session_id} | level={hint_info.get('hint_level')} | hint={hint_info.get('hint')!r} | remaining={hint_info.get('remaining_hints')}")
        else:
            logger.info(f"[HINT] session_id={request.session_id} | 提示次数已用完")

        return create_response(
            success=True,
            message="提示获取成功",
            data=hint_info
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HINT] session_id={request.session_id} | 获取提示失败: {e}", exc_info=True)
        return create_response(
            success=False,
            message="获取提示失败",
            error=str(e)
        )

@app.post("/api/game/end", response_model=GameResponse)
async def end_game(request: EndRequest):
    """End the game"""
    try:
        game_session, agent = get_session_pair(request.session_id)

        status_info = game_session.get_game_status()
        figure_name = game_session.current_figure.get("name", "未知")
        status_info["figure_name"] = figure_name

        logger.info(f"[END] session_id={request.session_id} | figure={figure_name} | is_correct={game_session.is_correct} | questions_asked={game_session.questions_asked} | hints_used={game_session.hints_used}")

        # Remove from active sessions
        del active_sessions[request.session_id]

        return create_response(
            success=True,
            message="游戏结束",
            data=status_info
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[END] session_id={request.session_id} | 结束游戏失败: {e}", exc_info=True)
        return create_response(
            success=False,
            message="结束游戏失败",
            error=str(e)
        )

@app.get("/api/game/status/{session_id}", response_model=GameResponse)
async def get_game_status(session_id: str):
    """Get game status"""
    try:
        game_session, agent = get_session_pair(session_id)

        return create_response(
            success=True,
            message="状态获取成功",
            data=game_session.get_game_status()
        )
    except HTTPException:
        raise
    except Exception as e:
        return create_response(
            success=False,
            message="状态获取失败",
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)