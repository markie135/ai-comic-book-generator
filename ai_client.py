"""
ai_client.py — Wrapper voor OpenAI (tekst) en Replicate (afbeeldingen).

Laadt API-keys automatisch uit .env via python-dotenv.
Beide clients zijn optioneel: als een key ontbreekt valt het systeem terug op
placeholders zodat de rest van de pipeline gewoon door kan draaien.
"""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Callable

# Laad .env als het bestaat
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv niet geïnstalleerd — werkt ook zonder


LogFn = Callable[[str], None]

# ---------------------------------------------------------------------------
# Configuratie uit omgeving
# ---------------------------------------------------------------------------

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
REPLICATE_MODEL: str = os.getenv(
    "REPLICATE_MODEL",
    "stability-ai/sdxl:39ed52f2319f9c539a5cbe73a5e8d1af7e96f783d3f7e3e8a9a7f7b5e0cfb5e1",
)
IMAGE_WIDTH: int = int(os.getenv("IMAGE_WIDTH", "1200"))
IMAGE_HEIGHT: int = int(os.getenv("IMAGE_HEIGHT", "1700"))


# ---------------------------------------------------------------------------
# Publieke API
# ---------------------------------------------------------------------------

def has_openai() -> bool:
    return bool(OPENAI_API_KEY and OPENAI_API_KEY != "sk-...")


def has_replicate() -> bool:
    return bool(REPLICATE_API_TOKEN and REPLICATE_API_TOKEN != "r8_...")


def generate_text(system_prompt: str, user_prompt: str, max_tokens: int = 512) -> str:
    """
    Roept OpenAI Chat Completions aan.
    Geeft de gegenereerde tekst terug, of een leeg string bij fout/geen key.
    """
    if not has_openai():
        return ""

    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.8,
        )
        content = response.choices[0].message.content
        return (content or "").strip()
    except Exception as exc:
        return f"[OpenAI fout: {exc}]"


def generate_image(prompt: str, output_path: Path, log: LogFn = print) -> bool:
    """
    Genereert een afbeelding via Replicate SDXL en slaat deze op als PNG.
    Geeft True terug bij succes, False bij fout/geen key.
    """
    if not has_replicate():
        return False

    try:
        import replicate  # type: ignore

        log(f"  Replicate: afbeelding genereren voor {output_path.name}...")
        output = replicate.run(
            REPLICATE_MODEL,
            input={
                "prompt": prompt,
                "negative_prompt": (
                    "color, modern clothing, extra characters, style break, "
                    "low-detail faces, photorealistic, blurry"
                ),
                "width": IMAGE_WIDTH,
                "height": IMAGE_HEIGHT,
                "num_outputs": 1,
                "scheduler": "K_EULER",
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
            },
        )

        # Replicate geeft een lijst van URL's of file-objecten terug
        result = output[0] if isinstance(output, list) else output
        _download_to_path(result, output_path)
        log(f"  Afbeelding opgeslagen: {output_path.name}")
        return True

    except Exception as exc:
        log(f"  [Replicate fout] {exc}")
        return False


# ---------------------------------------------------------------------------
# Hulpfuncties
# ---------------------------------------------------------------------------

def _download_to_path(source: object, dest: Path) -> None:
    """Download URL of lees file-achtig object naar dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    if hasattr(source, "read"):
        # File-achtig object (Replicate FileOutput)
        dest.write_bytes(source.read())
    elif isinstance(source, str) and source.startswith("http"):
        with urllib.request.urlopen(source) as resp:  # noqa: S310
            dest.write_bytes(resp.read())
    else:
        raise ValueError(f"Onbekend output type van Replicate: {type(source)}")
