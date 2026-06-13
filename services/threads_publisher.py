from __future__ import annotations

import asyncio
import hashlib
import hmac
import time
import re
from dataclasses import dataclass
from urllib.parse import urlencode, urlparse
from typing import Any

import requests

from services.meta_publish import load_export_package
from services.threads_publish import build_threads_publish_plan

GITHUB_URL_RE = re.compile(r"https?://(?:www\.)?(?:github\.com|gist\.github\.com)/\S+")


@dataclass(frozen=True)
class ThreadsPublishResult:
    success: bool
    published_id: str | None = None
    creation_id: str | None = None
    error_message: str | None = None


class ThreadsPublisher:
    def __init__(
        self,
        access_token: str,
        bot=None,
        user_id: str = "me",
        api_base: str = "https://graph.threads.net/v1.0",
        media_proxy_base_url: str | None = None,
        media_proxy_secret: str | None = None,
        media_proxy_ttl_seconds: int = 300,
        media_proxy_bot_alias: str | None = None,
        max_text_length: int = 450,
        timeout_seconds: int = 30,
    ):
        self.access_token = access_token
        self.bot = bot
        self.user_id = user_id or "me"
        self.api_base = api_base.rstrip("/")
        self.media_proxy_base_url = media_proxy_base_url.rstrip("/") if media_proxy_base_url else None
        self.media_proxy_secret = media_proxy_secret
        self.media_proxy_ttl_seconds = media_proxy_ttl_seconds
        self.media_proxy_bot_alias = (media_proxy_bot_alias or "").strip()
        self.max_text_length = max_text_length
        self.timeout_seconds = timeout_seconds

    async def publish_export(
        self,
        export_dir: str,
        public_base_url: str | None = None,
        caption_override: str | None = None,
    ) -> ThreadsPublishResult:
        try:
            plan = build_threads_publish_plan(
                export_dir=export_dir,
                public_base_url=public_base_url,
                caption_override=caption_override,
            )
            creation_id = await self._create_carousel_container(plan)
            if not creation_id:
                return ThreadsPublishResult(
                    success=False,
                    error_message="Failed to create Threads carousel container.",
                )

            await self._wait_for_container(creation_id)
            published_id = await self._publish_container(creation_id)
            comment_text = self._build_github_comment(plan.export_package)
            if comment_text:
                await self._publish_reply(comment_text, published_id)
            return ThreadsPublishResult(
                success=True,
                published_id=published_id,
                creation_id=creation_id,
            )
        except Exception as exc:
            return ThreadsPublishResult(
                success=False,
                error_message=str(exc),
            )

    async def validate_connection(self) -> bool:
        try:
            data = await self._request_json(
                "GET",
                f"{self.api_base}/me",
                params={"fields": "id,username"},
            )
            return bool(data.get("id"))
        except Exception:
            return False

    async def _create_carousel_container(self, plan) -> str | None:
        media_items = await self._load_export_media(export_dir=str(plan.export_package.export_dir))

        children: list[str] = []
        for item in media_items:
            child_id = await self._create_container(
                {
                    "media_type": "IMAGE",
                    "image_url": await self._telegram_file_url(item["file_id"]),
                    "is_carousel_item": "true",
                }
            )
            if not child_id:
                raise RuntimeError("Failed to create Threads carousel child container.")
            await self._wait_for_container(child_id)
            children.append(child_id)

        return await self._create_container(
            {
                "media_type": "CAROUSEL",
                "children": ",".join(children),
                "text": self._truncate_text(plan.parent_text),
            }
        )

    async def _create_container(self, payload: dict[str, str]) -> str | None:
        data = await self._request_json(
            "POST",
            f"{self.api_base}/{self.user_id}/threads",
            data=payload,
        )
        return data.get("id")

    async def _publish_container(self, creation_id: str) -> str:
        data = await self._request_json(
            "POST",
            f"{self.api_base}/{self.user_id}/threads_publish",
            data={"creation_id": creation_id},
        )
        published_id = data.get("id")
        if not published_id:
            raise RuntimeError("Threads publish did not return a published id.")
        return str(published_id)

    async def _publish_reply(self, text: str, reply_to_id: str) -> None:
        creation_id = await self._create_container(
            {
                "media_type": "TEXT",
                "text": self._truncate_text(text),
                "reply_to_id": reply_to_id,
            }
        )
        if creation_id:
            await self._publish_container(creation_id)

    async def _wait_for_container(self, creation_id: str, attempts: int = 15, delay: float = 2.0) -> None:
        for _ in range(attempts):
            status, error_message = await self._get_container_status(creation_id)
            if status in {"FINISHED", "PUBLISHED"}:
                return
            if status in {"ERROR", "EXPIRED"}:
                suffix = f": {error_message}" if error_message else ""
                raise RuntimeError(f"Threads container {creation_id} status={status}{suffix}")
            await asyncio.sleep(delay)
        raise RuntimeError(f"Threads container {creation_id} did not finish in time.")

    async def _get_container_status(self, creation_id: str) -> tuple[str, str | None]:
        data = await self._request_json(
            "GET",
            f"{self.api_base}/{creation_id}",
            params={"fields": "status,error_message"},
        )
        return str(data.get("status", "UNKNOWN")), data.get("error_message")

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        data: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._request_json_sync,
            method,
            url,
            data,
            params,
        )

    def _request_json_sync(
        self,
        method: str,
        url: str,
        data: dict[str, str] | None,
        params: dict[str, str] | None,
    ) -> dict[str, Any]:
        response = requests.request(
            method=method,
            url=url,
            data=data,
            params=params,
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=self.timeout_seconds,
        )
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        if response.status_code >= 400:
            message = payload.get("error", {}).get("message") or str(payload)
            raise RuntimeError(message)
        return payload

    def _truncate_text(self, text: str) -> str:
        text = (text or "").strip()
        if len(text) <= self.max_text_length:
            return text

        truncated = text[: self.max_text_length - 1].rstrip()
        if " " in truncated:
            truncated = truncated.rsplit(" ", 1)[0]
        return truncated.rstrip(" ,.;:-") + "…"

    def _build_github_comment(self, export_package) -> str | None:
        github_links: list[str] = []
        for source in (
            export_package.caption or "",
            str(export_package.metadata.get("source_text") or ""),
        ):
            for link in GITHUB_URL_RE.findall(source):
                if link not in github_links:
                    github_links.append(link)

        if not github_links:
            return None

        return "GitHub:\n" + "\n".join(github_links[:5])

    async def _load_export_media(self, export_dir: str) -> list[dict[str, Any]]:
        export_package = load_export_package(export_dir)
        media_items = export_package.metadata.get("telegram_media_items") or []
        if not media_items:
            raise RuntimeError(
                "Export does not contain Telegram media references yet. Regenerate the carousel and try again."
            )
        return media_items

    async def _telegram_file_url(self, file_id: str) -> str:
        if not self.bot:
            raise RuntimeError("Threads media publishing requires Telegram bot access.")
        if not self.media_proxy_base_url or not self.media_proxy_secret:
            raise RuntimeError(
                "Threads media publishing requires THREADS_MEDIA_PROXY_BASE_URL and THREADS_MEDIA_PROXY_SECRET."
            )

        file_obj = await self.bot.get_file(file_id)
        if not file_obj.file_path:
            raise RuntimeError(f"Telegram file path missing for media item {file_id}")

        normalized_path = self._normalize_telegram_file_path(file_obj.file_path)
        return self._build_signed_media_url(normalized_path)

    def _normalize_telegram_file_path(self, file_path: str) -> str:
        if file_path.startswith("http://") or file_path.startswith("https://"):
            parsed = urlparse(file_path)
            marker = f"/file/bot{self.bot.token}/"
            if marker in parsed.path:
                return parsed.path.split(marker, 1)[1]
            return parsed.path.lstrip("/")
        return file_path.lstrip("/")

    def _build_signed_media_url(self, file_path: str) -> str:
        ttl = self.media_proxy_ttl_seconds
        expires = str(int((time.time() + ttl) * 1000))
        prefix = f"{self.media_proxy_bot_alias}:" if self.media_proxy_bot_alias else ""
        payload = f"{prefix}{file_path}:{expires}".encode("utf-8")
        signature = hmac.new(
            self.media_proxy_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        query_payload = {
            "path": file_path,
            "expires": expires,
            "sig": signature,
        }
        if self.media_proxy_bot_alias:
            query_payload["bot"] = self.media_proxy_bot_alias
        query = urlencode(query_payload)
        return f"{self.media_proxy_base_url}/proxy/telegram-media?{query}"
