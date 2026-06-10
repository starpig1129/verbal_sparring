import os
from pathlib import Path
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory paths
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_DEFAULT_ENV_FILE = Path(__file__).parent.parent / ".env"
_ENV_FILE = os.getenv("ENV_FILE", str(_DEFAULT_ENV_FILE))

_SETTINGS_YAML = Path(__file__).parent.parent / "config" / "settings.yaml"

# Load default values from settings.yaml
if _SETTINGS_YAML.exists():
    with open(_SETTINGS_YAML, "r", encoding="utf-8") as f:
        _yaml_defaults = yaml.safe_load(f) or {}
else:
    _yaml_defaults = {}


class Settings(BaseSettings):
    database_url: str
    test_database_url: str = ""

    # Select backend: "vllm" or "ollama"
    model_provider: str = "vllm"

    # vLLM (OpenAI-compatible) settings
    vllm_url: str = "http://localhost:8001"
    vllm_api_key: str = "EMPTY"
    vllm_referee_model: str = "referee-agent"
    vllm_player_model: str = "player-agent"

    # Ollama settings
    ollama_url: str = "http://localhost:11434"
    ollama_referee_model: str = "gemma4:12b"
    ollama_player_model: str = "gemma4:12b"

    referee_temperature: float = 0.8
    player_temperature: float = 0.9

    # Generation caps shared by both providers; referee JSON and NPC taunts
    # are short, so a hard ceiling prevents runaway long generations.
    llm_max_tokens: int = 256
    # Ollama-only tuning: keep the model resident between rounds and pin the
    # context window so an oversized prompt fails loudly instead of silently
    # truncating the system prompt.
    ollama_keep_alive: str = "30m"
    ollama_num_ctx: int = 4096
    
    # Path to prompts configuration file
    prompts_yaml_path: str = "src/backend/config/prompts.yaml"
    
    # Authentication settings
    secret_key: str
    access_token_expire_minutes: int = 10080

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore", protected_namespaces=())


# Precedence merger: settings.yaml (lowest) < .env file < os.environ (highest)
_merged_config = {}

# 1. Apply yaml defaults
for k, v in _yaml_defaults.items():
    _merged_config[k.lower()] = v

# 2. Apply .env overrides
_env_path = Path(_ENV_FILE)
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                val = val.strip().strip("'\"")
                _merged_config[key.strip().lower()] = val

# 3. Apply os.environ overrides
for k, v in os.environ.items():
    _merged_config[k.lower()] = v

# Initialize settings with merged configurations.
settings = Settings(**_merged_config)

# Resolve prompts YAML path (convert to absolute if relative)
_prompts_path = Path(settings.prompts_yaml_path)
if not _prompts_path.is_absolute():
    _prompts_path = _REPO_ROOT / _prompts_path

# Load YAML prompts
with open(_prompts_path, "r", encoding="utf-8") as f:
    _prompts_data = yaml.safe_load(f)

REFEREE_SYSTEM_PROMPT = _prompts_data["referee"]["system_prompt"].strip()
REFEREE_FEW_SHOTS = [
    (shot["input"], shot["output"]) for shot in _prompts_data["referee"]["few_shots"]
]
# Rotating referee personas; empty list disables style injection entirely.
REFEREE_STYLES = [
    {"name": s["name"], "directive": s["directive"]}
    for s in _prompts_data["referee"].get("styles", [])
]
NPC_SYSTEM_PROMPT = _prompts_data["npc"]["system_prompt"].strip()
# The 8 fighting schools the player LoRA was trained on; empty disables.
NPC_GENRES = [
    {
        "key": g["key"],
        "name": g["name"],
        "display": g["display"],
        "directive": g["directive"],
    }
    for g in _prompts_data["npc"].get("genres", [])
]
MEMORY_ANALYSIS_PROMPT = _prompts_data["memory_analysis"]["system_prompt"].strip()


def make_chat_llm(model_key: str, temperature: float):
    """Return a LangChain chat model for the configured provider.

    Selects ChatOpenAI (vLLM) or ChatOllama based on settings.model_provider.
    Both expose the same LangChain BaseChatModel interface so callers need
    not know which backend is in use.

    For vLLM, thinking is disabled via extra_body so the model outputs answers
    directly without emitting chain-of-thought tokens.

    Args:
        model_key: "referee" or "player" — resolves to the configured model name.
        temperature: Sampling temperature for this LLM role.

    Returns:
        A LangChain BaseChatModel instance ready for .ainvoke().
    """
    if settings.model_provider == "vllm":
        from langchain_openai import ChatOpenAI
        model_name = (
            settings.vllm_referee_model if model_key == "referee"
            else settings.vllm_player_model
        )
        return ChatOpenAI(
            base_url=f"{settings.vllm_url}/v1",
            api_key=settings.vllm_api_key,
            model=model_name,
            temperature=temperature,
            max_tokens=settings.llm_max_tokens,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
    else:
        from langchain_ollama import ChatOllama
        model_name = (
            settings.ollama_referee_model if model_key == "referee"
            else settings.ollama_player_model
        )
        return ChatOllama(
            base_url=settings.ollama_url,
            model=model_name,
            temperature=temperature,
            num_predict=settings.llm_max_tokens,
            num_ctx=settings.ollama_num_ctx,
            keep_alive=settings.ollama_keep_alive,
        )
