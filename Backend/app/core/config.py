from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "amzur-ai-chat"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_EXPIRE_MINUTES: int = 480

    # Database (optional for chatbot-only mode)
    DATABASE_URL: Optional[str] = None

    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    # Frontend CORS
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # Employee auth domains (comma separated in env, e.g. stackyon.com,amzur.com)
    EMPLOYEE_EMAIL_DOMAINS: str = "stackyon.com,amzur.com"

    # Amzur LiteLLM Proxy
    LITELLM_PROXY_URL: str
    LITELLM_VIRTUAL_KEY: str
    LLM_MODEL: str = "gemini/gemini-2.5-flash"
    LITELLM_EMBEDDING_MODEL: str = "text-embedding-3-large"
    IMAGE_GEN_MODEL: str = "gemini/imagen-4.0-fast-generate-001"
    LITELLM_USER_ID: Optional[str] = None

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # Google Sheets
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None

    # NL-to-SQL
    SQL_QUERY_ALLOWED_TABLES: str = "chat_threads,chat_messages,profiles,attachments"

    # Conversational memory
    MEMORY_WINDOW_SIZE: int = 5  # number of recent exchanges sent to LLM

    # File uploads
    MAX_UPLOAD_MB: int = 20
    UPLOAD_DIR: str = "./uploads"
    # Note: generated_image files are created server-side and do not rely on upload MIME allow-list.
    ALLOWED_UPLOAD_MIMES: str = (
        "image/jpeg,image/png,image/gif,image/webp,"
        "video/mp4,video/webm,video/quicktime,"
        "application/pdf,"
        "text/plain,text/x-python,text/javascript,text/html,text/css,text/markdown,application/json,"
        "text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,"
        "application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
