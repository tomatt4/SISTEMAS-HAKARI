from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _optional_int(name: str) -> int | None:
    value = os.getenv(name, "").strip()
    return int(value) if value else None


@dataclass(frozen=True)
class BotConfig:
    token: str
    prefix: str
    port: int
    ticket_category_id: int | None
    support_role_id: int | None
    ticket_panel_image_url: str


def load_config() -> BotConfig:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise RuntimeError("A variavel DISCORD_TOKEN nao foi definida no ambiente.")

    return BotConfig(
        token=token,
        prefix=os.getenv("PREFIX", ",").strip() or ",",
        port=int(os.getenv("PORT", "3000")),
        ticket_category_id=_optional_int("TICKET_CATEGORY_ID"),
        support_role_id=_optional_int("SUPPORT_ROLE_ID"),
        ticket_panel_image_url=os.getenv("TICKET_PANEL_IMAGE_URL", "").strip(),
    )
