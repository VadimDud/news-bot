import asyncio
import html
import json
import logging
import re
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message

from .. import config
from ..i18n import t

router = Router()
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_AI_TIMEOUT = 180
_MAX_MSG = 4000

_ai_session: str | None = None
_ai_lock = asyncio.Lock()


def _is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID


async def _run_opencode(prompt: str, session_id: str | None) -> tuple[str, str | None]:
    """Run opencode non-interactively; return (reply_text, session_id)."""
    cmd = ["opencode", "run", "--format", "json", "--title", "tg-admin", "--agent", "chat"]
    if session_id:
        cmd += ["-s", session_id]
    cmd.append(prompt)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(PROJECT_ROOT),
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=_AI_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError("opencode run timed out")

    new_session = session_id
    reply_parts: list[str] = []
    for line in out.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "step_start":
            sid = event.get("sessionID")
            if sid:
                new_session = sid
        elif event.get("type") == "text":
            text = (event.get("part") or {}).get("text")
            if text:
                reply_parts.append(_ANSI_RE.sub("", text))
    return "".join(reply_parts).strip(), new_session


async def _send_chunks(message: Message, text: str):
    for i in range(0, len(text), _MAX_MSG):
        await message.answer(html.escape(text[i:i + _MAX_MSG]))


@router.message(F.text.regexp(r"^/ai\b"))
async def cmd_ai(message: Message, user_lang: str):
    if not _is_admin(message.from_user.id):
        await message.answer(t(user_lang, "admin_not_admin"))
        return

    prompt = re.sub(r"^/ai(@[A-Za-z0-9_]+)?\s*", "", message.text, count=1).strip()
    if not prompt:
        await message.answer(t(user_lang, "ai_usage"))
        return
    if _ai_lock.locked():
        await message.answer(t(user_lang, "ai_busy"))
        return

    global _ai_session
    async with _ai_lock:
        working = await message.answer(t(user_lang, "ai_working"))
        try:
            reply, sid = await _run_opencode(prompt, _ai_session)
        except FileNotFoundError:
            log.error("[AI] opencode binary not found")
            await message.answer(t(user_lang, "ai_no_binary"))
            return
        except TimeoutError:
            log.warning("[AI] opencode run timed out")
            await message.answer(t(user_lang, "ai_timeout"))
            return
        except Exception as e:
            log.error(f"[AI] opencode run failed: {e}")
            await message.answer(t(user_lang, "ai_error"))
            return
        finally:
            try:
                await working.delete()
            except Exception:
                pass

        if sid:
            _ai_session = sid
        if not reply:
            await message.answer(t(user_lang, "ai_error"))
            return
        await _send_chunks(message, reply)


@router.message(F.text.regexp(r"^/ai_reset(@[A-Za-z0-9_]+)?$"))
async def cmd_ai_reset(message: Message, user_lang: str):
    if not _is_admin(message.from_user.id):
        await message.answer(t(user_lang, "admin_not_admin"))
        return
    global _ai_session
    _ai_session = None
    await message.answer(t(user_lang, "ai_reset_done"))
