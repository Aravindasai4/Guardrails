from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Guardrails++"
    environment: str = "dev"

    model_config = SettingsConfigDict(env_file=".env")
