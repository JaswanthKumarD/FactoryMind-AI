"""Very small demo login system for the hackathon prototype.

For a production system, use a proper user database and password hashing library.
"""

import hashlib
import secrets

ADMIN_PASSWORD_HASH = hashlib.sha256(b"FactoryMind@123").hexdigest()


def login(username, password):
    """Validate the demo administrator account and create a session token."""
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    if username == "admin" and password_hash == ADMIN_PASSWORD_HASH:
        return {
            "username": "admin",
            "role": "Administrator",
            "token": secrets.token_hex(24),
        }

    return None
