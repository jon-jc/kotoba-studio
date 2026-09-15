"""Japanese and English voice workflows for Kotoba Studio."""

import os

# Set before importing Hub clients; model downloads are explicit user actions.
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["DO_NOT_TRACK"] = "1"

__version__ = "0.12.5"
