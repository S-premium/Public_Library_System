#!/usr/bin/env python3
"""
decrypt_tool.py
---------------
Terminal utility to decrypt data encrypted with the Fernet keys used by
Library Management System V3 (ENCRYPTION_KEY, PII_ENCRYPTION_KEY,
EMAIL_ENCRYPTION_KEY).

Usage:
    python decrypt_tool.py
    python decrypt_tool.py --key pii
    python decrypt_tool.py --env /path/to/.env

Run this from (or point --env at) the project folder that contains your
.env file, since it reads the same keys your app uses.
"""

import os
import sys
import getpass
import argparse
from cryptography.fernet import Fernet, InvalidToken

try:
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependency. Install it with: pip install python-dotenv cryptography --break-system-packages")
    sys.exit(1)

try:
    import bcrypt
except ImportError:
    bcrypt = None


KEY_ENV_NAMES = {
    "data": "ENCRYPTION_KEY",
    "pii": "PII_ENCRYPTION_KEY",
    "email": "EMAIL_ENCRYPTION_KEY",
}


def load_ciphers(env_path: str | None):
    if not env_path:
        env_path = os.path.join(os.getcwd(), ".env")

    if not os.path.isfile(env_path):
        print(f"Could not find .env at: {env_path}")
        print("Run this script from your project folder, or pass --env /path/to/.env")
        sys.exit(1)

    load_dotenv(env_path, override=True)

    ciphers = {}
    missing = []
    for label, env_name in KEY_ENV_NAMES.items():
        val = os.getenv(env_name)
        if not val:
            missing.append(env_name)
            continue
        try:
            ciphers[label] = Fernet(val.encode())
        except Exception as e:
            print(f"Warning: {env_name} is present but not a valid Fernet key ({e})")

    if missing:
        print("Warning: these keys were not found in the .env: " + ", ".join(missing))

    if not ciphers:
        print("No valid encryption keys were loaded. Check your .env path/contents.")
        sys.exit(1)

    return ciphers


def pick_cipher(ciphers: dict, requested: str | None):
    if requested:
        if requested not in ciphers:
            print(f"Key '{requested}' not available. Available: {', '.join(ciphers.keys())}")
            sys.exit(1)
        return requested

    if len(ciphers) == 1:
        return next(iter(ciphers))

    print("\nAvailable keys:")
    labels = list(ciphers.keys())
    for i, label in enumerate(labels, start=1):
        print(f"  {i}. {label}  ({KEY_ENV_NAMES[label]})")
    print(f"  {len(labels)+1}. try all keys automatically")
    print(f"  {len(labels)+2}. check a password against a bcrypt hash (instead of decrypting)")

    choice = input("select key: ").strip()
    if choice == str(len(labels) + 1):
        return "auto"
    if choice == str(len(labels) + 2):
        return "password"
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(labels):
            return labels[idx]
    except ValueError:
        pass
    print("Invalid choice.")
    sys.exit(1)


def decrypt_with(cipher: Fernet, token: str) -> str:
    return cipher.decrypt(token.encode()).decode()


def check_password_mode():
    if bcrypt is None:
        print("Missing dependency. Install it with: pip install bcrypt --break-system-packages")
        sys.exit(1)

    print("\nPassword check mode — bcrypt hashes can't be decrypted, only checked against a guess.")
    print("(input is hidden while typing; press ctrl+C to cancel)\n")
    while True:
        stored_hash = input("enter stored hash (or 'q' to quit): ").strip()
        if stored_hash.lower() in ("q", "quit", "exit"):
            break
        if not stored_hash:
            continue
        guess = getpass.getpass("enter password to test: ")
        try:
            match = bcrypt.checkpw(guess.encode(), stored_hash.encode())
            print("MATCH ✅\n" if match else "NO MATCH ❌\n")
        except ValueError as e:
            print(f"invalid hash format: {e}\n")


def main():
    parser = argparse.ArgumentParser(description="Decrypt Fernet-encrypted fields / check bcrypt password hashes from the library DB.")
    parser.add_argument("--key", choices=list(KEY_ENV_NAMES.keys()) + ["password"], default=None,
                         help="which key to use: data, pii, email — or 'password' to check a password against a bcrypt hash")
    parser.add_argument("--env", default=None, help="path to the .env file (defaults to ./.env)")
    args = parser.parse_args()

    if args.key == "password":
        check_password_mode()
        return

    ciphers = load_ciphers(args.env)
    selection = pick_cipher(ciphers, args.key)

    if selection == "password":
        check_password_mode()
        return

    print()
    while True:
        token = input("enter encrypted data (or 'q' to quit): ").strip()
        if token.lower() in ("q", "quit", "exit"):
            break
        if not token:
            continue

        if selection == "auto":
            result = None
            for label, cipher in ciphers.items():
                try:
                    result = decrypt_with(cipher, token)
                    print(f"decrypted ({label}): {result}\n")
                    break
                except InvalidToken:
                    continue
            if result is None:
                print("decrypted: <failed to decrypt with any available key — invalid token or wrong key>\n")
        else:
            cipher = ciphers[selection]
            try:
                result = decrypt_with(cipher, token)
                print(f"decrypted: {result}\n")
            except InvalidToken:
                print("decrypted: <failed — invalid token or wrong key for this field>\n")


if __name__ == "__main__":
    main()
