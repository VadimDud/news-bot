import hashlib
import hmac
import time

import pytest
from aiohttp.test_utils import TestClient, TestServer

from bot import database as db
from web_app import create_app

TEST_TOKEN = "test-token-123"


@pytest.fixture
async def client():
    app = create_app()
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    yield client
    await client.close()


async def _grant_user(user_id: int = 123, days: int = 30):
    await db.set_user(user_id, "testuser", "Test User", "ru")
    await db.grant_access(user_id, days)


async def _login(client, user_id: int = 123):
    resp = await client.post("/auth/manual", data={"user_id": user_id}, allow_redirects=False)
    assert resp.status == 302
    assert "/channels" in resp.headers["Location"]


def _telegram_payload(user_id: int = 123, token: str = TEST_TOKEN) -> dict:
    data = {
        "id": user_id,
        "first_name": "Test",
        "username": "testuser",
        "auth_date": str(int(time.time())),
    }
    data_check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    secret = hashlib.sha256(token.encode()).digest()
    data["hash"] = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    return data


class TestAuth:
    async def test_index_page(self, client):
        resp = await client.get("/")
        assert resp.status == 200
        text = await resp.text()
        assert "Вход" in text
        assert "Войти по Telegram ID вручную" in text

    async def test_index_redirects_when_logged_in(self, client):
        await _grant_user()
        await _login(client)
        resp = await client.get("/", allow_redirects=False)
        assert resp.status == 302
        assert "/channels" in resp.headers["Location"]

    async def test_protected_page_redirects_to_login(self, client):
        resp = await client.get("/channels", allow_redirects=False)
        assert resp.status == 302
        assert resp.headers["Location"] == "/"

    async def test_manual_login_unregistered(self, client):
        resp = await client.post("/auth/manual", data={"user_id": 999}, allow_redirects=False)
        assert resp.status == 200
        assert "не зарегистрированы" in await resp.text()

    async def test_manual_login_without_access(self, client):
        await db.set_user(123, "testuser", "Test User", "ru")
        resp = await client.post("/auth/manual", data={"user_id": 123}, allow_redirects=False)
        assert resp.status == 200
        assert "Доступ ещё не активирован" in await resp.text()

    async def test_manual_login_bad_id(self, client):
        resp = await client.post("/auth/manual", data={"user_id": "abc"}, allow_redirects=False)
        assert resp.status == 200
        assert "Укажите корректный Telegram ID" in await resp.text()

    async def test_telegram_login(self, client):
        await _grant_user()
        resp = await client.post("/auth/telegram", json=_telegram_payload(), allow_redirects=False)
        assert resp.status == 200
        assert (await resp.json())["ok"] is True
        channels = await client.get("/channels", allow_redirects=False)
        assert channels.status == 200
        assert "Вы вошли как пользователь" in await channels.text()

    async def test_telegram_login_unregistered(self, client):
        resp = await client.post("/auth/telegram", json=_telegram_payload(user_id=999), allow_redirects=False)
        assert resp.status == 403
        assert "не зарегистрированы" in (await resp.json())["error"]

    async def test_telegram_login_bad_hash(self, client):
        await _grant_user()
        payload = _telegram_payload()
        payload["hash"] = "0" * 64
        resp = await client.post("/auth/telegram", json=payload, allow_redirects=False)
        assert resp.status == 400
        assert (await resp.json())["ok"] is False

    async def test_logout(self, client):
        await _grant_user()
        await _login(client)
        resp = await client.post("/logout", allow_redirects=False)
        assert resp.status == 302
        resp = await client.get("/channels", allow_redirects=False)
        assert resp.status == 302


class TestChannelCreate:
    async def test_create_channel(self, client):
        await _grant_user()
        await _login(client)
        resp = await client.post("/channels", data={
            "name": "Макро",
            "keywords": "инфляция, ключевая ставка",
            "ticker": "sber",
            "source_tags": ["macro"],
            "topics": ["finance"],
        }, allow_redirects=False)
        assert resp.status == 302
        assert resp.headers["Location"] == "/channels"

        channels = await db.get_user_channels(123)
        assert len(channels) == 1
        ch = channels[0]
        assert ch["name"] == "Макро"
        assert ch["keywords"] == ["инфляция", "ключевая ставка"]
        assert ch["ticker"] == "SBER"
        assert ch["source_tags"] == ["macro"]
        assert ch["topics"] == ["finance"]

    async def test_create_without_source_tags_means_all(self, client):
        await _grant_user()
        await _login(client)
        resp = await client.post("/channels", data={
            "name": "Все источники",
            "keywords": "нефть",
        }, allow_redirects=False)
        assert resp.status == 302
        ch = (await db.get_user_channels(123))[0]
        assert ch["source_tags"] == []

    async def test_invalid_source_tags_ignored(self, client):
        await _grant_user()
        await _login(client)
        await client.post("/channels", data={
            "name": "Тест",
            "keywords": "нефть",
            "source_tags": ["bogus_tag"],
        }, allow_redirects=False)
        ch = (await db.get_user_channels(123))[0]
        assert ch["source_tags"] == []

    async def test_duplicate_name(self, client):
        await _grant_user()
        await _login(client)
        data = {"name": "Дубль", "keywords": "нефть"}
        resp = await client.post("/channels", data=data, allow_redirects=False)
        assert resp.status == 302
        resp = await client.post("/channels", data=data, allow_redirects=False)
        assert resp.status == 200
        assert "уже существует" in await resp.text()
        assert len(await db.get_user_channels(123)) == 1

    async def test_missing_name_and_keywords(self, client):
        await _grant_user()
        await _login(client)
        resp = await client.post("/channels", data={}, allow_redirects=False)
        assert resp.status == 200
        text = await resp.text()
        assert "Название ленты должно содержать" in text
        assert "хотя бы одно ключевое слово" in text

    async def test_escapes_html(self, client):
        await _grant_user()
        await _login(client)
        await client.post("/channels", data={
            "name": "<script>alert(1)</script>",
            "keywords": "нефть",
        }, allow_redirects=False)
        resp = await client.get("/channels")
        text = await resp.text()
        assert "<script>alert(1)</script>" not in text
        assert "&lt;script&gt;" in text


class TestChannelEdit:
    async def test_edit_form_prefilled(self, client):
        await _grant_user()
        await _login(client)
        await db.create_channel(123, "Макро", ["инфляция"], "sber", ["macro"], ["finance"])
        channel_id = (await db.get_user_channels(123))[0]["id"]
        resp = await client.get(f"/channels/{channel_id}/edit")
        assert resp.status == 200
        text = await resp.text()
        assert "Макро" in text
        assert "инфляция" in text
        assert "SBER" in text

    async def test_edit_foreign_channel_not_allowed(self, client):
        await _grant_user()
        await _grant_user(456, days=30)
        await _login(client)
        await db.create_channel(456, "Чужая", ["нефть"])
        channel_id = (await db.get_user_channels(456))[0]["id"]
        resp = await client.get(f"/channels/{channel_id}/edit")
        assert resp.status == 200
        assert "Лента не найдена" in await resp.text()

    async def test_update_channel(self, client):
        await _grant_user()
        await _login(client)
        await db.create_channel(123, "Макро", ["инфляция"], "sber", ["macro"], ["finance"])
        channel_id = (await db.get_user_channels(123))[0]["id"]
        resp = await client.post(f"/channels/{channel_id}", data={
            "name": "Макро 2",
            "keywords": "цб, ставка",
            "ticker": "sber",
            "source_tags": ["macro", "finance"],
            "topics": ["macro"],
        }, allow_redirects=False)
        assert resp.status == 302
        ch = await db.get_channel(channel_id)
        assert ch["name"] == "Макро 2"
        assert ch["keywords"] == ["цб", "ставка"]
        assert ch["source_tags"] == ["macro", "finance"]
        assert ch["topics"] == ["macro"]

    async def test_update_to_duplicate_name(self, client):
        await _grant_user()
        await _login(client)
        await db.create_channel(123, "Первая", ["нефть"])
        await db.create_channel(123, "Вторая", ["газ"])
        target = (await db.get_user_channels(123))[1]["id"]
        resp = await client.post(f"/channels/{target}", data={
            "name": "Первая",
            "keywords": "газ",
        }, allow_redirects=False)
        assert resp.status == 200
        assert "уже существует" in await resp.text()


class TestChannelDelete:
    async def test_delete_channel(self, client):
        await _grant_user()
        await _login(client)
        await db.create_channel(123, "Лента", ["нефть"])
        channel_id = (await db.get_user_channels(123))[0]["id"]
        resp = await client.post(f"/channels/{channel_id}/delete", allow_redirects=False)
        assert resp.status == 302
        assert await db.get_user_channels(123) == []

    async def test_delete_channel_htmx(self, client):
        await _grant_user()
        await _login(client)
        await db.create_channel(123, "Лента", ["нефть"])
        channel_id = (await db.get_user_channels(123))[0]["id"]
        resp = await client.post(
            f"/channels/{channel_id}/delete",
            headers={"HX-Request": "true"},
            allow_redirects=False,
        )
        assert resp.status == 200
        assert resp.headers.get("HX-Redirect") == "/channels"
        assert await db.get_user_channels(123) == []

    async def test_delete_foreign_channel_not_allowed(self, client):
        await _grant_user()
        await _grant_user(456, days=30)
        await _login(client)
        await db.create_channel(456, "Чужая", ["нефть"])
        channel_id = (await db.get_user_channels(456))[0]["id"]
        resp = await client.post(f"/channels/{channel_id}/delete", allow_redirects=False)
        assert resp.status == 200
        assert "Лента не найдена" in await resp.text()
        assert len(await db.get_user_channels(456)) == 1


class TestChannelList:
    async def test_list_empty(self, client):
        await _grant_user()
        await _login(client)
        resp = await client.get("/channels")
        assert resp.status == 200
        assert "Создать ленту" in await resp.text()

    async def test_list_shows_channel(self, client):
        await _grant_user()
        await _login(client)
        await db.create_channel(123, "Макро", ["инфляция", "цб"], "sber", ["macro"], ["finance"])
        resp = await client.get("/channels")
        text = await resp.text()
        assert "Макро" in text
        assert "инфляция, цб" in text
        assert "SBER" in text
