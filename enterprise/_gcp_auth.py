"""
Shared GCP auth helper for the Fortified Enterprise Fleet components.

Reads a service account key from the FIRESTORE_CREDENTIALS_JSON env var
(the JSON content itself, not a file path) - this is the Vercel-friendly
pattern, since serverless functions don't reliably have a persistent
filesystem to point GOOGLE_APPLICATION_CREDENTIALS at. Falls back to
Application Default Credentials (useful when running locally in a
Codespace with `gcloud auth application-default login`), and finally to
None if neither is configured - callers treat None as "use the in-memory
fallback store".
"""

from __future__ import annotations
import json
import os


def get_firestore_client():
    try:
        from google.cloud import firestore

        creds_json = os.environ.get("FIRESTORE_CREDENTIALS_JSON")
        if creds_json:
            from google.oauth2 import service_account
            info = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(info)
            return firestore.Client(credentials=credentials, project=info.get("project_id"))

        # Falls back to Application Default Credentials if no explicit
        # JSON was provided - works locally with `gcloud auth
        # application-default login` or GOOGLE_APPLICATION_CREDENTIALS
        # pointing at a real file on disk.
        return firestore.Client()
    except Exception:
        return None
