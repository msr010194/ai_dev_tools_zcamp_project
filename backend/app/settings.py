"""Typed application settings, read from `NOTES_*` environment variables."""

import secrets

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NOTES_")

    app_name: str = "Notes API"
    # Signs timeline cursors. Random per app by default, so cursors don't survive a restart;
    # set NOTES_CURSOR_SECRET to share cursors across restarts or instances.
    cursor_secret: str = Field(default_factory=lambda: secrets.token_hex(32))
