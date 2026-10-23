"""Settings read from environment variables. No secrets are stored here."""

import os

DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def cors_origins() -> list[str]:
    """Browser origins allowed to call the API.

    Set VERIFIGST_CORS_ORIGINS to a comma-separated list to change them. A wildcard is
    refused: the API must only answer the frontends that are listed.
    """
    raw = os.environ.get("VERIFIGST_CORS_ORIGINS", "")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    if "*" in origins:
        raise ValueError("VERIFIGST_CORS_ORIGINS must list explicit origins, not *")
    return origins or list(DEFAULT_CORS_ORIGINS)
