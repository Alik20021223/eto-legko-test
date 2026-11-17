from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    keitaro_url: str = "https://tlgk.host"
    keitaro_api_key: str = ""
    database_url: str = "sqlite:///./app.db"

    # Реквизиты, с которыми создаётся каждая кампания (ищутся в Keitaro по имени).
    campaign_domain: str = "kylovoa.com"
    campaign_group: str = "FORTESTS"
    campaign_traffic_source: str = "FORTESTS"
    # Куда первый поток отправляет трафик, попавший под фильтр страны.
    fallback_url: str = "https://google.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
