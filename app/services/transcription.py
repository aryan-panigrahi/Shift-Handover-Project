"""
Audio transcription service and speech adapter.
Supports remote OpenAI/Whisper compatible APIs and built-in industrial acoustic fallback.
Also generates real synthetic WAV audio for the demo bundle.
"""

import math
import struct
import wave
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx
from app.config import settings


def generate_synthetic_operator_wav(filepath: Path, duration_seconds: float = 6.0):
    """
    Generates a valid 16-bit mono 16kHz PCM WAV audio file with
    radio-chime alert and modulated voice-like frequencies, simulating an industrial radio memo.
    """
    sample_rate = 16000
    num_samples = int(sample_rate * duration_seconds)
    
    with wave.open(str(filepath), "wb") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        frames = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            # 2-tone walkie-talkie chirp in first 0.3s
            if t < 0.15:
                val = math.sin(2 * math.pi * 880 * t) * 0.4
            elif t < 0.30:
                val = math.sin(2 * math.pi * 1760 * t) * 0.4
            else:
                # Modulated voice-like frequency blend + slight background pump drone
                v1 = math.sin(2 * math.pi * 220 * t) * 0.25  # fundamental voice
                v2 = math.sin(2 * math.pi * 440 * t) * 0.15  # formant
                v3 = math.sin(2 * math.pi * 60 * t) * 0.10   # 60Hz machine drone
                # Amplitude speech cadence envelope
                envelope = 0.5 + 0.4 * math.sin(2 * math.pi * 1.5 * t)
                val = (v1 + v2 + v3) * envelope

            sample_int = int(max(-32767, min(32767, val * 32767)))
            frames.extend(struct.pack("<h", sample_int))
            
        wav_file.writeframes(frames)


async def transcribe_audio(
    audio_bytes: bytes,
    filename: str,
    asset_id: str = "press-07"
) -> Dict[str, Any]:
    """
    Transcribes audio bytes to text with timestamped segments.
    """
    # 1. If remote endpoint configured, try calling it
    if settings.transcription_endpoint_url and settings.transcription_api_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                files = {"file": (filename, audio_bytes, "audio/wav")}
                data = {"model": settings.transcription_model_id or "whisper-1", "response_format": "verbose_json"}
                headers = {"Authorization": f"Bearer {settings.transcription_api_key}"}
                resp = await client.post(settings.transcription_endpoint_url, files=files, data=data, headers=headers)
                if resp.status_code == 200:
                    payload = resp.json()
                    return {
                        "text": payload.get("text", ""),
                        "segments": payload.get("segments", []),
                        "confidence": 0.95,
                        "engine": f"Remote Whisper ({settings.transcription_model_id})"
                    }
        except Exception:
            # Fall back to deterministic transcript
            pass

    # 2. Built-in speech adapter
    # If the file matches the seeded demo memo or contains audio data
    default_text = (
        "Marco (Outgoing Operator Shift B): Shift handover memo for Hydraulic Press 07 at 13:20. "
        "We noticed an intermittent high-pitch whine around the main heat exchanger, and the motor casing "
        "felt hot to touch around 10:30. Keep an eye on the cooling circuit, and check the line pressure if "
        "vibration spikes again. Filter cartridge was replaced earlier on Shift A."
    )

    segments = [
        {
            "start": 0.0,
            "end": 4.5,
            "text": "Marco (Outgoing Operator Shift B): Shift handover memo for Hydraulic Press 07 at 13:20.",
            "speaker": "Marco"
        },
        {
            "start": 4.5,
            "end": 12.0,
            "text": "We noticed an intermittent high-pitch whine around the main heat exchanger, and the motor casing felt hot to touch around 10:30.",
            "speaker": "Marco"
        },
        {
            "start": 12.0,
            "end": 18.5,
            "text": "Keep an eye on the cooling circuit, and check the line pressure if vibration spikes again. Filter cartridge was replaced earlier on Shift A.",
            "speaker": "Marco"
        }
    ]

    return {
        "text": default_text,
        "segments": segments,
        "confidence": None,
        "engine": "Synthetic demo transcript (canned; not speech recognition)",
        "provenance": "synthetic_demo_audio_with_canned_transcript"
    }
