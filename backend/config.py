"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_path: str = "whop.db"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    default_forecast_horizon: int = 6
    default_mc_simulations: int = 100

    # LLM provider: "none", "ollama", "llamacpp", "vllm", "claude", "openai"
    llm_provider: str = "none"

    # Ollama (local, no API key needed)
    ollama_model: str = "llama3"
    ollama_base_url: str = "http://localhost:11434"

    # llama.cpp server (local, no API key needed)
    llamacpp_server_url: str = "http://localhost:8080"

    # vLLM server (local, no API key needed — serves HuggingFace models)
    vllm_server_url: str = "http://localhost:8000"
    vllm_model: str = "meta-llama/Llama-3-8b-chat-hf"

    # Anthropic Claude (cloud, requires API key)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # OpenAI (cloud, requires API key)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Shared LLM settings
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048
    llm_timeout_seconds: float = 30.0

    model_config = {"env_file": ".env", "env_prefix": "WHOP_"}


settings = Settings()
