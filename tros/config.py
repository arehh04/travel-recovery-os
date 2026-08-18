"""TR-OS configuration constants."""

import os
from pathlib import Path

# Load .env file if present (before any os.environ reads)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv not installed — rely on environment variables

# --- Atlas CLI ---
ATLAS_CLI_BINARY = os.environ.get("ATLAS_CLI_BINARY", "atlas-flight")
ATLAS_SEARCH_TIMEOUT_SECONDS = int(os.environ.get("ATLAS_SEARCH_TIMEOUT", "60"))

# --- Mission defaults ---
DEFAULT_CURRENCY = os.environ.get("TROS_CURRENCY", "USD")
DEFAULT_BUDGET_LIMIT = float(os.environ.get("TROS_BUDGET_LIMIT", "1000"))

# --- Flight ranking weights (must sum to 1.0) ---
RANKING_WEIGHT_ARRIVAL = 0.35
RANKING_WEIGHT_COST = 0.25
RANKING_WEIGHT_DELAY = 0.20
RANKING_WEIGHT_STOPS = 0.10
RANKING_WEIGHT_PREFERENCE = 0.10

# --- Confidence thresholds ---
CONFIDENCE_HIGH = 0.70
CONFIDENCE_MEDIUM = 0.40

# --- Retry ---
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1.0

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- LLM Configuration (Phase 3: Agentic AI layer) ---
LLM_PROVIDER = os.environ.get("TR_OS_LLM_PROVIDER", "openai")
LLM_MODEL = os.environ.get("TR_OS_LLM_MODEL", "gpt-4o-mini")
LLM_API_KEY = os.environ.get("TR_OS_LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("TR_OS_LLM_BASE_URL", "") or None
LLM_TEMPERATURE = float(os.environ.get("TR_OS_LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS = int(os.environ.get("TR_OS_LLM_MAX_TOKENS", "2000"))
LLM_TIMEOUT = int(os.environ.get("TR_OS_LLM_TIMEOUT", "30"))

# --- ReAct loop bounds (Phase 4: True ReAct tool-calling) ---
LLM_MAX_TOOL_CALLS = int(os.environ.get("TR_OS_LLM_MAX_TOOL_CALLS", "3"))

# --- Recovery bounds (Phase 6: bounded recovery) ---
LLM_MAX_RECOVERY_ATTEMPTS = int(os.environ.get("TR_OS_MAX_RECOVERY_ATTEMPTS", "2"))

# --- Timeouts (Phase 7: production hardening) ---
MISSION_TIMEOUT_SECONDS = int(os.environ.get("TR_OS_MISSION_TIMEOUT", "300"))
LLM_TIMEOUT_SECONDS = LLM_TIMEOUT  # alias for clarity
ATLAS_TIMEOUT_SECONDS = ATLAS_SEARCH_TIMEOUT_SECONDS  # alias for clarity
