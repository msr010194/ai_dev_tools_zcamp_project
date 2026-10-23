"""Typed application settings, read from `NOTES_*` environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NOTES_")

    app_name: str = "Notes API"
