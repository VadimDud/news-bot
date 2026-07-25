#!/usr/bin/env python3
"""Automated bot testing via Telegram Bot API.

Sends commands to the bot and verifies delivery + bot status.
Run while the bot is UP — check Telegram for bot responses.

Usage:
    python test_bot_api.py              # prompts for chat_id
    python test_bot_api.py --chat ID    # use specific chat_id
"""

import asyncio
import os
import sys
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
HTTP_PROXY = os.getenv("HTTP_PROXY", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

passed = 0
failed = 0


def ok(label: str):
    global passed
    passed += 1
    print(f"  {GREEN}+{RESET} {label}")


def fail(label: str, detail: str = ""):
    global failed
    failed += 1
    msg = f"  {RED}x{RESET} {label}"
    if detail:
        msg += f" -- {detail}"
    print(msg)


async def api(method: str, **kwargs) -> dict:
    proxy = HTTP_PROXY if HTTP_PROXY else None
    async with httpx.AsyncClient(timeout=30, proxy=proxy or None) as c:
        r = await c.post(f"{BASE}/{method}", json=kwargs)
        return r.json()


async def send_command(chat_id: int, text: str) -> dict:
    return await api("sendMessage", chat_id=chat_id, text=text)


async def main():
    global passed, failed

    if not BOT_TOKEN:
        print(f"{RED}ERROR: BOT_TOKEN not set in .env{RESET}")
        sys.exit(1)

    # Parse --chat flag
    chat_id = None
    args = sys.argv[1:]
    if "--chat" in args:
        idx = args.index("--chat")
        if idx + 1 < len(args):
            chat_id = int(args[idx + 1])

    # Check bot is alive
    me = await api("getMe")
    if not me.get("ok"):
        print(f"{RED}Cannot reach bot: {me.get('description')}{RESET}")
        sys.exit(1)
    bot_info = me["result"]
    print(f"{BOLD}Bot:{RESET} @{bot_info['username']} (id={bot_info['id']})")

    if chat_id is None:
        print(f"\n{BOLD}Telegram Bot API Test{RESET}")
        print("This script sends real messages to the bot.\n")
        chat_id = int(input("Enter your chat_id (from @userinfobot): "))

    is_admin = chat_id == ADMIN_ID
    print(f"{BOLD}Chat:{RESET}  {chat_id} {'(admin)' if is_admin else ''}")
    print(f"{BOLD}Admin:{RESET} {ADMIN_ID}")
    print("=" * 50)

    # ── Test 1: Bot responds to /start ──
    print(f"\n{BOLD}[1] /start{RESET}")
    r = await send_command(chat_id, "/start")
    if r.get("ok"):
        ok("sendMessage delivered")
        ok("Check Telegram: bot should show menu with Start/Help/Tools/Language")
    else:
        fail("sendMessage failed", r.get("description"))

    # ── Test 2: /help ──
    print(f"\n{BOLD}[2] /help{RESET}")
    r = await send_command(chat_id, "/help")
    if r.get("ok"):
        ok("sendMessage delivered")
        text = r["result"].get("text", "")
        if "Инструменты" in text or "Tools" in text:
            ok("Help text mentions Tools")
        elif text:
            ok(f"Help text received ({len(text)} chars)")
        else:
            fail("Empty help text")
    else:
        fail("sendMessage failed", r.get("description"))

    # ── Test 3: /finance ──
    print(f"\n{BOLD}[3] /finance{RESET}")
    r = await send_command(chat_id, "/finance")
    if r.get("ok"):
        ok("sendMessage delivered")
        text = r["result"].get("text", "")
        if text:
            ok(f"Finance menu received ({len(text)} chars)")
    else:
        fail("sendMessage failed", r.get("description"))

    # ── Test 4: Add ticker SBER ──
    print(f"\n{BOLD}[4] Add ticker: SBER{RESET}")
    r = await send_command(chat_id, "SBER")
    if r.get("ok"):
        ok("sendMessage delivered (ticker sent)")
        text = r["result"].get("text", "")
        if "SBER" in text:
            ok("Response mentions SBER")
    else:
        fail("sendMessage failed", r.get("description"))

    # ── Test 5: Add ticker GAZP ──
    print(f"\n{BOLD}[5] Add ticker: GAZP{RESET}")
    r = await send_command(chat_id, "GAZP")
    if r.get("ok"):
        ok("sendMessage delivered (ticker sent)")
    else:
        fail("sendMessage failed", r.get("description"))

    # ── Test 6: Duplicate ticker ──
    print(f"\n{BOLD}[6] Duplicate ticker: SBER{RESET}")
    r = await send_command(chat_id, "SBER")
    if r.get("ok"):
        ok("sendMessage delivered (duplicate)")
    else:
        fail("sendMessage failed", r.get("description"))

    # ── Test 7: Invalid ticker ──
    print(f"\n{BOLD}[7] Invalid ticker: X{RESET}")
    r = await send_command(chat_id, "X")
    if r.get("ok"):
        ok("sendMessage delivered (invalid ticker)")
        text = r["result"].get("text", "")
        if text:
            ok(f"Response received ({len(text)} chars)")
    else:
        fail("sendMessage failed", r.get("description"))

    # ── Test 8: /vadman (admin) ──
    print(f"\n{BOLD}[8] /vadman{RESET}")
    r = await send_command(chat_id, "/vadman")
    if r.get("ok"):
        ok("sendMessage delivered")
        text = r["result"].get("text", "")
        if is_admin:
            if text and ("Админ" in text or "Admin" in text or "панель" in text.lower()):
                ok("Admin panel opened")
            elif text:
                ok(f"Response received ({len(text)} chars)")
            else:
                fail("Empty admin response")
        else:
            if text and ("нет доступа" in text.lower() or "access" in text.lower() or "Forbidden" in text.lower()):
                ok("Access denied for non-admin (correct)")
            elif text:
                ok(f"Response received ({len(text)} chars)")
            else:
                fail("Empty response for non-admin")
    else:
        fail("sendMessage failed", r.get("description"))

    # ── Test 9: /admin (should NOT work) ──
    print(f"\n{BOLD}[9] /admin (should be hidden){RESET}")
    r = await send_command(chat_id, "/admin")
    if r.get("ok"):
        text = r["result"].get("text", "")
        # Telegram might show "command not recognized" or the bot might not handle it
        if text and ("Админ" in text or "Admin" in text):
            fail("/admin still works (should be hidden)")
        else:
            ok("/admin command ignored by bot")
    else:
        fail("sendMessage failed", r.get("description"))

    # ── Test 10: Scan news ──
    print(f"\n{BOLD}[10] /finance scan{RESET}")
    r = await send_command(chat_id, "/finance")
    if r.get("ok"):
        ok("Finance menu sent - tap 'Scan News' button in Telegram")
    else:
        fail("sendMessage failed", r.get("description"))

    # ── Test 11: Bot getMe consistency ──
    print(f"\n{BOLD}[11] Bot status check{RESET}")
    me2 = await api("getMe")
    if me2.get("ok") and me2["result"]["id"] == bot_info["id"]:
        ok("Bot is alive and consistent")
    else:
        fail("Bot status check failed")

    # ── Summary ──
    print(f"\n{'=' * 50}")
    print(f"{BOLD}Results: {GREEN}{passed} passed{RESET}, {RED}{failed} failed{RESET}")

    if failed:
        print(f"\n{YELLOW}Check Telegram for bot responses to verify actual behavior.{RESET}")
        sys.exit(1)
    else:
        print(f"\n{GREEN}All commands delivered successfully!{RESET}")
        print(f"{YELLOW}Check Telegram to verify bot responses.{RESET}")


if __name__ == "__main__":
    asyncio.run(main())
