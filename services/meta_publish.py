from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

DEFAULT_GRAPH_HOST = "graph.instagram.com"
DEFAULT_GRAPH_API_VERSION = "v24.0"
MAX_CAROUSEL_ITEMS = 10


@dataclass(frozen=True)
class MetaAppConfig:
    app_id: str
    app_secret: str
    redirect_uri: str
    graph_host: str = DEFAULT_GRAPH_HOST
    graph_api_version: str = DEFAULT_GRAPH_API_VERSION
    webhook_callback_url: str | None = None
    webhook_verify_token: str | None = None
    deauth_callback_url: str | None = None
    data_deletion_request_url: str | None = None

    @property
    def api_base_url(self) -> str:
        version = self.graph_api_version.strip("/")
        return f"https://{self.graph_host}/{version}"


@dataclass(frozen=True)
class MetaCredentials:
    ig_user_id: str
    access_token: str
    token_expires_at: str | None = None
    username: str | None = None


MetaInstagramCredentials = MetaCredentials


@dataclass(frozen=True)
class ExportPackage:
    export_dir: Path
    slides: tuple[str, ...]
    caption: str
    metadata: dict[str, Any]

    @property
    def export_slug(self) -> str:
        return self.export_dir.name


@dataclass(frozen=True)
class HttpRequest:
    method: str
    url: str
    payload: dict[str, str]


@dataclass(frozen=True)
class GraphRequestTemplate:
    method: str
    path: str
    payload: dict[str, str]
    response_binding: str | None = None
    depends_on: tuple[str, ...] = ()

    def render(
        self,
        config: MetaAppConfig,
        bindings: dict[str, str] | None = None,
    ) -> HttpRequest:
        values = bindings or {}
        rendered_path = self.path.format(**values)
        rendered_payload = {
            key: value.format(**values) for key, value in self.payload.items()
        }
        return HttpRequest(
            method=self.method,
            url=f"{config.api_base_url}{rendered_path}",
            payload=rendered_payload,
        )


@dataclass(frozen=True)
class MediaUploadSpec:
    slide_filename: str
    public_url: str
    request: GraphRequestTemplate


@dataclass(frozen=True)
class StatusPollPlan:
    container_binding: str
    interval_seconds: int = 60
    max_attempts: int = 5
    terminal_statuses: tuple[str, ...] = ("FINISHED", "ERROR", "EXPIRED")
    request_template: GraphRequestTemplate = field(
        default_factory=lambda: GraphRequestTemplate(
            method="GET",
            path="/{container_id}",
            payload={"fields": "status_code", "access_token": "{access_token}"},
        )
    )

    def render(
        self,
        config: MetaAppConfig,
        container_id: str,
        access_token: str = "{access_token}",
    ) -> HttpRequest:
        return self.request_template.render(
            config,
            {"container_id": container_id, "access_token": access_token},
        )


@dataclass(frozen=True)
class CarouselPublishPlan:
    export_package: ExportPackage
    media_uploads: tuple[MediaUploadSpec, ...]
    create_carousel_request: GraphRequestTemplate
    publish_request: GraphRequestTemplate
    poll_child_plan: StatusPollPlan
    poll_carousel_plan: StatusPollPlan


def load_export_package(export_dir: str | Path) -> ExportPackage:
    base_path = Path(export_dir)
    metadata_path = base_path / "metadata.json"
    caption_path = base_path / "caption.txt"

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    caption = caption_path.read_text(encoding="utf-8").strip()
    slides = tuple(metadata.get("slides", ()))

    if not slides:
        raise ValueError("Export package does not contain any slides.")

    return ExportPackage(
        export_dir=base_path,
        slides=slides,
        caption=caption,
        metadata=metadata,
    )


def build_carousel_publish_plan(
    export_dir: str | Path,
    public_base_url: str,
    credentials: MetaCredentials,
    config: MetaAppConfig | None = None,
    caption_override: str | None = None,
    max_items: int = MAX_CAROUSEL_ITEMS,
) -> CarouselPublishPlan:
    export_package = load_export_package(export_dir)
    if len(export_package.slides) > max_items:
        raise ValueError("Instagram carousel publishing supports up to 10 items.")

    base_url = public_base_url.rstrip("/")
    uploads: list[MediaUploadSpec] = []
    child_bindings: list[str] = []

    for index, filename in enumerate(export_package.slides, start=1):
        binding = f"child_{index:02d}_container_id"
        child_bindings.append(binding)
        public_url = _build_public_slide_url(base_url, export_package.export_slug, filename)
        uploads.append(
            MediaUploadSpec(
                slide_filename=filename,
                public_url=public_url,
                request=GraphRequestTemplate(
                    method="POST",
                    path=f"/{credentials.ig_user_id}/media",
                    payload={
                        "image_url": public_url,
                        "is_carousel_item": "true",
                        "access_token": "{access_token}",
                    },
                    response_binding=binding,
                ),
            )
        )

    caption = (caption_override or export_package.caption).strip()
    carousel_request = GraphRequestTemplate(
        method="POST",
        path=f"/{credentials.ig_user_id}/media",
        payload={
            "media_type": "CAROUSEL",
            "children": ",".join(f"{{{binding}}}" for binding in child_bindings),
            "caption": caption,
            "access_token": "{access_token}",
        },
        response_binding="carousel_container_id",
        depends_on=tuple(child_bindings),
    )
    publish_request = GraphRequestTemplate(
        method="POST",
        path=f"/{credentials.ig_user_id}/media_publish",
        payload={
            "creation_id": "{carousel_container_id}",
            "access_token": "{access_token}",
        },
        depends_on=("carousel_container_id",),
    )

    return CarouselPublishPlan(
        export_package=export_package,
        media_uploads=tuple(uploads),
        create_carousel_request=carousel_request,
        publish_request=publish_request,
        poll_child_plan=StatusPollPlan(container_binding="child_container_id"),
        poll_carousel_plan=StatusPollPlan(container_binding="carousel_container_id"),
    )


def _build_public_slide_url(public_base_url: str, export_slug: str, filename: str) -> str:
    quoted_slug = quote(export_slug)
    quoted_filename = quote(filename)
    return f"{public_base_url}/{quoted_slug}/{quoted_filename}"
