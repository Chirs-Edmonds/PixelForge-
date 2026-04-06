"""
tripo3d.py — PixelForge Phase 3

Generates a .glb mesh from a text prompt or image using the Tripo3D v2 REST API.

Usage:
    python scripts/tripo3d.py --prompt "a fantasy sword" --outfile assets/sword.glb
    python scripts/tripo3d.py --image reference.png --outfile assets/character.glb

Arguments:
    --prompt  TEXT   Text description for text-to-3D generation (mutually exclusive with --image)
    --image   PATH   Image file for image-to-3D generation (mutually exclusive with --prompt)
    --outfile PATH   Where to save the downloaded .glb (default: assets/generated.glb)
    --api-key STRING Override API key from .env (optional)
    --timeout INT    Maximum wait time in seconds (default: 300)

API key is read from .env at project root: TRIPO3D_API_KEY=your_key
Install: py -3.12 -m pip install requests python-dotenv
"""

import argparse
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    raise SystemExit(
        "[PixelForge] requests is not installed.\n"
        "Run: py -3.12 -m pip install requests python-dotenv"
    )

try:
    from dotenv import load_dotenv
except ImportError:
    raise SystemExit(
        "[PixelForge] python-dotenv is not installed.\n"
        "Run: py -3.12 -m pip install requests python-dotenv"
    )

PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE     = PROJECT_ROOT / ".env"
ASSETS_DIR   = PROJECT_ROOT / "assets"

BASE_URL      = "https://api.tripo3d.ai/v2/openapi"
POLL_INTERVAL = 5    # seconds between status polls
MAX_WAIT      = 300  # default timeout in seconds


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a .glb mesh via Tripo3D API."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", type=str, help="Text prompt for text-to-3D generation.")
    group.add_argument("--image",  type=str, help="Image path for image-to-3D generation.")

    parser.add_argument("--outfile", type=str, default=None,
                        help="Output .glb path. Default: assets/generated.glb")
    parser.add_argument("--api-key", type=str, default=None,
                        help="Tripo3D API key. Overrides TRIPO3D_API_KEY in .env.")
    parser.add_argument("--timeout", type=int, default=MAX_WAIT,
                        help=f"Max wait seconds (default: {MAX_WAIT}).")
    return parser.parse_args()


def get_api_key(cli_key):
    if cli_key:
        return cli_key
    load_dotenv(ENV_FILE)
    key = os.environ.get("TRIPO3D_API_KEY")
    if not key or key == "your_key_here":
        raise SystemExit(
            "[PixelForge] Tripo3D API key not set.\n"
            f"Edit {ENV_FILE} and set: TRIPO3D_API_KEY=your_actual_key\n"
            "Or pass: --api-key YOUR_KEY"
        )
    return key


def upload_image(image_path: Path, headers: dict) -> str:
    """Upload an image to Tripo3D and return the file_token."""
    print(f"[PixelForge] Uploading image: {image_path}")
    url = f"{BASE_URL}/upload"
    with open(image_path, "rb") as f:
        resp = requests.post(url, headers=headers, files={"file": (image_path.name, f, "image/png")})
    resp.raise_for_status()
    data = resp.json()
    if data.get("code", -1) != 0:
        raise RuntimeError(f"[PixelForge] Image upload failed: {data}")
    token = data["data"]["image_token"]
    print(f"[PixelForge] Image uploaded. Token: {token[:12]}...")
    return token


def create_task(task_body: dict, headers: dict) -> str:
    """Create a Tripo3D task and return the task_id."""
    url = f"{BASE_URL}/task"
    resp = requests.post(url, headers=headers, json=task_body)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code", -1) != 0:
        raise RuntimeError(f"[PixelForge] Task creation failed: {data}")
    task_id = data["data"]["task_id"]
    print(f"[PixelForge] Task created: {task_id}")
    return task_id


def poll_task(task_id: str, headers: dict, timeout: int) -> str:
    """Poll task status until success. Returns the model download URL."""
    url = f"{BASE_URL}/task/{task_id}"
    start = time.time()

    print(f"[PixelForge] Polling task {task_id} (timeout: {timeout}s)...")
    while True:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code", -1) != 0:
            raise RuntimeError(f"[PixelForge] Status poll error: {data}")

        task = data["data"]
        status   = task.get("status", "unknown")
        progress = task.get("progress", 0)

        print(f"[PixelForge]   {status} ({progress}%)")

        if status == "success":
            model_url = task.get("output", {}).get("model")
            if not model_url:
                raise RuntimeError(f"[PixelForge] Task succeeded but no model URL in output: {task}")
            return model_url

        if status == "failed":
            raise RuntimeError(f"[PixelForge] Tripo3D task failed: {task}")

        elapsed = time.time() - start
        if elapsed > timeout:
            raise TimeoutError(
                f"[PixelForge] Timed out after {timeout}s waiting for task {task_id}.\n"
                "Try --timeout 600 for complex models."
            )

        time.sleep(POLL_INTERVAL)


def download_glb(url: str, outfile: Path) -> None:
    """Download the .glb file from the signed URL."""
    print(f"[PixelForge] Downloading .glb from Tripo3D...")
    outfile.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    with open(outfile, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    size_kb = outfile.stat().st_size // 1024
    print(f"[PixelForge] Saved: {outfile}  ({size_kb} KB)")


def main():
    args = parse_args()
    api_key = get_api_key(args.api_key)
    outfile = Path(args.outfile) if args.outfile else ASSETS_DIR / "generated.glb"
    outfile = outfile.resolve()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print(f"[PixelForge] tripo3d.py starting")
    print(f"[PixelForge] Mode   : {'text-to-3D' if args.prompt else 'image-to-3D'}")
    print(f"[PixelForge] Input  : {args.prompt or args.image}")
    print(f"[PixelForge] Output : {outfile}")

    # Build task body
    if args.prompt:
        task_body = {
            "type": "text_to_model",
            "prompt": args.prompt,
        }
    else:
        image_path = Path(args.image).resolve()
        if not image_path.exists():
            raise FileNotFoundError(f"[PixelForge] Image not found: {image_path}")
        # Image upload needs multipart — temporarily remove Content-Type to let requests set it
        upload_headers = {"Authorization": f"Bearer {api_key}"}
        file_token = upload_image(image_path, upload_headers)
        task_body = {
            "type": "image_to_model",
            "file": {
                "type": image_path.suffix.lstrip(".").lower(),
                "file_token": file_token,
            },
        }

    task_id   = create_task(task_body, headers)
    model_url = poll_task(task_id, headers, args.timeout)
    download_glb(model_url, outfile)

    print(f"[PixelForge] tripo3d.py complete. Mesh saved to: {outfile}")


if __name__ == "__main__":
    main()
