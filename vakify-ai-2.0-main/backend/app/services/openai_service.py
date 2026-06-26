import json
import os
import re
import time
from typing import Any
from pathlib import Path
from math import gcd

import requests


OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech"
OPENAI_IMAGE_URL = "https://api.openai.com/v1/images/generations"
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1/text-to-speech"
LEONARDO_BASE_URL = "https://cloud.leonardo.ai/api/rest/v1"
NVIDIA_IMAGE_URL = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-3-medium"
OPENAI_DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4").strip() or "gpt-5.4"
OPENAI_FAST_MODEL = os.getenv("OPENAI_FAST_MODEL", "gpt-5.4-mini").strip() or "gpt-5.4-mini"


def _extract_text(payload: dict[str, Any]) -> str:
    if payload.get("output_text"):
        return str(payload["output_text"]).strip()

    text_parts: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                text_parts.append(content["text"])
    return "\n".join(text_parts).strip()


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None

    # Handle markdown code fences.
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
    if fenced:
        text = fenced.group(1)

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    # Best-effort extraction of the first JSON object.
    direct = re.search(r"\{[\s\S]*\}", text)
    if not direct:
        return None
    try:
        parsed = json.loads(direct.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _responses_request(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    response_format: dict[str, Any] | None = None,
    max_output_tokens: int | None = None,
) -> dict[str, Any] | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    payload: dict[str, Any] = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if response_format:
        payload["text"] = {"format": response_format}
    if max_output_tokens is not None:
        payload["max_output_tokens"] = max_output_tokens

    try:
        response = requests.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=35,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def _responses_output_text(data: dict[str, Any] | None) -> str | None:
    if not data:
        return None
    text = _extract_text(data)
    return text or None


def _extract_leonardo_generation_id(payload: dict[str, Any]) -> str:
    candidates = [
        payload.get("generationId"),
        payload.get("generation_id"),
        payload.get("id"),
    ]
    nested = payload.get("sdGenerationJob") or payload.get("sd_generation_job") or {}
    if isinstance(nested, dict):
        candidates.extend(
            [
                nested.get("generationId"),
                nested.get("generation_id"),
                nested.get("id"),
            ]
        )
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value:
            return value
    return ""


def _normalize_leonardo_model_id(raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        return ""
    aliases = {
        "lucid origin": "7b592283-e8a7-4c5a-9ba6-d18c31f258b9",
        "lucid-origin": "7b592283-e8a7-4c5a-9ba6-d18c31f258b9",
        "lucid realism": "05ce0082-2d80-4a2d-8653-4d1c85e2418e",
        "lucid-realism": "05ce0082-2d80-4a2d-8653-4d1c85e2418e",
        "leonardo phoenix 1.0": "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3",
        "leonardo-phoenix-1.0": "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3",
        "leonardo lightning xl": "b24e16ff-06e3-43eb-8d33-4416c2d75876",
        "leonardo-lightning-xl": "b24e16ff-06e3-43eb-8d33-4416c2d75876",
    }
    return aliases.get(value.lower(), value)


def chatgpt_json(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> dict[str, Any] | None:
    responses_data = _responses_request(
        model=OPENAI_FAST_MODEL,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    if responses_data:
        parsed = _extract_json(_responses_output_text(responses_data) or "")
        if parsed is not None:
            return parsed

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", OPENAI_DEFAULT_MODEL).strip() or OPENAI_DEFAULT_MODEL
    if not api_key:
        return None

    try:
        response = requests.post(
            OPENAI_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()
        content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
        return _extract_json(content)
    except Exception:
        return None


def chatgpt_text(system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str | None:
    responses_data = _responses_request(
        model=OPENAI_DEFAULT_MODEL,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
    )
    text = _responses_output_text(responses_data)
    if text:
        return text

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", OPENAI_DEFAULT_MODEL).strip() or OPENAI_DEFAULT_MODEL
    if not api_key:
        return None

    try:
        response = requests.post(
            OPENAI_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()
        text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
        return text or None
    except Exception:
        return None


def openai_json_schema(
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
    name: str,
    temperature: float = 0.2,
    model: str | None = None,
) -> dict[str, Any] | None:
    responses_data = _responses_request(
        model=model or OPENAI_FAST_MODEL,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        response_format={
            "type": "json_schema",
            "name": name,
            "schema": schema,
            "strict": True,
        },
    )
    if not responses_data:
        return None
    parsed = _extract_json(_responses_output_text(responses_data) or "")
    return parsed


def generate_tts_mp3(text: str, output_path: str) -> bool:
    if not text.strip():
        return False

    # Prefer ElevenLabs when key is available.
    eleven_api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    eleven_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL").strip()
    eleven_model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip()
    if eleven_api_key and eleven_voice_id:
        try:
            response = requests.post(
                f"{ELEVENLABS_BASE_URL}/{eleven_voice_id}",
                headers={
                    "xi-api-key": eleven_api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": text[:3500],
                    "model_id": eleven_model_id,
                    "voice_settings": {
                        "stability": 0.45,
                        "similarity_boost": 0.75,
                    },
                },
                timeout=25,
            )
            response.raise_for_status()
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(response.content)
            return True
        except Exception:
            # fall back to OpenAI TTS
            pass

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return False

    tts_model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts").strip()
    voice = os.getenv("OPENAI_TTS_VOICE", "alloy").strip()

    try:
        response = requests.post(
            OPENAI_SPEECH_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": tts_model,
                "voice": voice,
                "input": text[:4000],
                "format": "mp3",
            },
            timeout=20,
        )
        response.raise_for_status()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(response.content)
        return True
    except Exception:
        return False


def generate_image_data_url(prompt: str, size: str = "1024x1024") -> str | None:
    if not prompt.strip():
        return None

    leonardo_key = os.getenv("LEONARDO_API_KEY", "").strip()
    if leonardo_key:
        try:
            width = 1024
            height = 1024
            if "x" in size:
                w_raw, h_raw = size.lower().split("x", 1)
                width = max(256, min(1536, int(w_raw)))
                height = max(256, min(1536, int(h_raw)))

            payload: dict[str, Any] = {
                "prompt": prompt[:3200],
                "width": width,
                "height": height,
                "num_images": 1,
                "alchemy": True,
                "promptMagic": False,
                "highContrast": False,
                "public": False,
            }
            model_id = _normalize_leonardo_model_id(os.getenv("LEONARDO_MODEL_ID", "").strip())
            if model_id:
                payload["modelId"] = model_id

            response = requests.post(
                f"{LEONARDO_BASE_URL}/generations",
                headers={
                    "Authorization": f"Bearer {leonardo_key}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=35,
            )
            response.raise_for_status()
            generation_payload = response.json() or {}
            generation_id = _extract_leonardo_generation_id(generation_payload)
            if generation_id:
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    poll = requests.get(
                        f"{LEONARDO_BASE_URL}/generations/{generation_id}",
                        headers={
                            "Authorization": f"Bearer {leonardo_key}",
                            "Accept": "application/json",
                        },
                        timeout=30,
                    )
                    poll.raise_for_status()
                    data = poll.json() or {}
                    generation = data.get("generations_by_pk") or data.get("generation") or data
                    status = str(generation.get("status") or "").upper()
                    images = generation.get("generated_images") or []
                    if images and isinstance(images, list):
                        first = images[0] or {}
                        url = first.get("url") or first.get("image_url") or first.get("source") or first.get("thumbnailUrl")
                        if url:
                            return str(url)
                    if status == "COMPLETE" and not images:
                        time.sleep(2)
                        continue
                    time.sleep(2)
        except Exception:
            pass

    nvidia_key = os.getenv("NVIDIA_IMAGE_API_KEY", "").strip()
    nvidia_url = os.getenv("NVIDIA_IMAGE_URL", NVIDIA_IMAGE_URL).strip()
    if not nvidia_key or not nvidia_url:
        return None

    try:
        width = 1024
        height = 1024
        if "x" in size:
            w_raw, h_raw = size.lower().split("x", 1)
            width = max(256, min(1568, int(w_raw)))
            height = max(256, min(1568, int(h_raw)))
        ratio_gcd = gcd(width, height) or 1
        aspect_ratio = f"{width // ratio_gcd}:{height // ratio_gcd}"

        response = requests.post(
            nvidia_url,
            headers={
                "Authorization": f"Bearer {nvidia_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt[:3200],
                "cfg_scale": float(os.getenv("NVIDIA_IMAGE_CFG_SCALE", "5")),
                "aspect_ratio": os.getenv("NVIDIA_IMAGE_ASPECT_RATIO", aspect_ratio).strip() or aspect_ratio,
                "seed": int(os.getenv("NVIDIA_IMAGE_SEED", "0")),
                "steps": int(os.getenv("NVIDIA_IMAGE_STEPS", "50")),
                "negative_prompt": os.getenv("NVIDIA_IMAGE_NEGATIVE_PROMPT", ""),
            },
            timeout=35,
        )
        response.raise_for_status()
        payload = response.json()

        artifacts = payload.get("artifacts") or []
        if artifacts and isinstance(artifacts[0], dict):
            b64 = artifacts[0].get("base64")
            if b64:
                return f"data:image/png;base64,{b64}"

        data = payload.get("data") or []
        if data and isinstance(data[0], dict):
            b64 = data[0].get("b64_json")
            if b64:
                return f"data:image/png;base64,{b64}"
            url = data[0].get("url")
            if url:
                return str(url)

        if payload.get("image"):
            image_value = str(payload["image"])
            if image_value.startswith("data:image/"):
                return image_value
            return f"data:image/png;base64,{image_value}"
    except Exception:
        return None

    return None
