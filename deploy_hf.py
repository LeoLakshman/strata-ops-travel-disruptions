#!/usr/bin/env python3
"""
Deploy Strata Ops to Hugging Face Spaces.
Uses the official huggingface_hub Python SDK to create a Docker Space and upload files.
"""

import os
import sys
import argparse
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(Path.home() / ".env")
except ImportError:
    pass

def main():
    parser = argparse.ArgumentParser(description="Deploy Strata Ops to Hugging Face Spaces")
    parser.add_argument("--token", help="Hugging Face Access Token (Write permissions required)")
    parser.add_argument("--space-id", help="Hugging Face Space ID (e.g. username/strata-ops-travel)")
    parser.add_argument("--private", action="store_true", help="Set Space to private (default: public)")
    args = parser.parse_args()

    token = args.token or os.environ.get("HF_TOKEN")
    if not token:
        # Check token files
        token_paths = [
            Path.home() / ".cache" / "huggingface" / "token",
            Path.home() / ".huggingface" / "token",
        ]
        for p in token_paths:
            if p.exists():
                token = p.read_text().strip()
                break

    if not token:
        print("\n[!] Hugging Face Access Token not found.")
        print("    Please provide a token using --token <HF_TOKEN> or export HF_TOKEN=<HF_TOKEN>")
        print("    You can create a free token with Write permissions at: https://huggingface.co/settings/tokens\n")
        sys.exit(1)

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("[!] huggingface_hub is not installed. Run: pip install huggingface_hub")
        sys.exit(1)

    api = HfApi(token=token)

    try:
        user_info = api.whoami(token=token)
        username = user_info["name"]
        print(f"[+] Authenticated as Hugging Face user: {username}")
    except Exception as e:
        print(f"[!] Authentication failed: {e}")
        print("    Please verify your Hugging Face token at https://huggingface.co/settings/tokens")
        sys.exit(1)

    space_id = args.space_id or os.environ.get("HF_SPACE_ID")
    if not space_id:
        space_id = f"{username}/strata-ops-travel-disruptions"
    elif "/" not in space_id:
        space_id = f"{username}/{space_id}"

    print(f"[+] Target Space ID: {space_id}")
    print(f"[+] Ensuring Docker Space repository exists...")

    try:
        api.create_repo(
            repo_id=space_id,
            repo_type="space",
            space_sdk="docker",
            private=args.private,
            exist_ok=True,
            token=token,
        )
        print(f"[✓] Space repository ready: https://huggingface.co/spaces/{space_id}")
    except Exception as e:
        print(f"[!] Error creating space repo: {e}")
        sys.exit(1)

    print("[+] Uploading project code to Hugging Face...")
    current_dir = Path(__file__).resolve().parent

    ignore_patterns = [
        ".git/**",
        ".venv/**",
        ".pytest_cache/**",
        "__pycache__/**",
        "*.pyc",
        "*.pyo",
        "*.zip",
        ".env",
        ".DS_Store",
    ]

    try:
        commit_info = api.upload_folder(
            repo_id=space_id,
            folder_path=str(current_dir),
            repo_type="space",
            token=token,
            commit_message="Deploy Strata Ops Travel Disruption Intelligence to Hugging Face",
            ignore_patterns=ignore_patterns,
        )
        print(f"\n[✓] DEPLOYMENT COMPLETE!")
        print(f"    Live URL:  https://huggingface.co/spaces/{space_id}")
        print(f"    Direct UI: https://{space_id.replace('/', '-')}.hf.space")
        print("\n    Hugging Face is now building your Docker container.")
        print("    You can view real-time build logs at the URL above.\n")
    except Exception as e:
        print(f"[!] Error uploading folder: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
