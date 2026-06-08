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
    
    # Model configuration settings
    model_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_referee_model: str = "gemma4:12b"
    ollama_player_model: str = "gemma4:12b"
    
    vllm_url: str = "http://localhost:8001"
    vllm_referee_model: str = "referee-agent"
    vllm_player_model: str = "player-agent"
    
    referee_temperature: float = 0.8
    player_temperature: float = 0.9
    
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
NPC_SYSTEM_PROMPT = _prompts_data["npc"]["system_prompt"].strip()
