"""
Generate an ultrasonic tone above the human hearing range.

Human hearing typically ranges from 20 Hz to 20,000 Hz (20 kHz).
This script generates a sine wave at a frequency above 20 kHz,
which is inaudible to humans but can be emitted by speakers that
support the frequency (many smart speakers have tweeters capable
of reproducing frequencies up to ~24 kHz or higher).

Supports two modes:
  1. Local playback   – plays directly via sounddevice
  2. WAV file export  – saves a .wav file that can be served to
                        Home Assistant's media_player.play_media service

Requirements:
    pip install numpy sounddevice requests

Usage:
    # Local playback
    python ultrasonic_tone.py

    # Save WAV file only (no playback)
    python ultrasonic_tone.py --save ultrasonic.wav

    # Send to a Home Assistant media player entity
    python ultrasonic_tone.py --ha-url http://homeassistant.local:8123 \
                              --ha-token YOUR_LONG_LIVED_TOKEN \
                              --entity media_player.living_room_speaker
"""

import argparse
import io
import wave

import numpy as np


# --- Configuration ---
FREQUENCY_HZ = 22000      # 22 kHz – above the ~20 kHz human hearing ceiling
DURATION_S = 5             # play for 5 seconds
SAMPLE_RATE = 48000        # samples per second (must be > 2x frequency per Nyquist)
AMPLITUDE = 0.8            # 0.0 – 1.0 (fraction of full scale)


def generate_tone(freq: float, duration: float, sample_rate: int, amplitude: float) -> np.ndarray:
    """Return a NumPy array containing a pure sine-wave tone."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def save_wav(samples: np.ndarray, sample_rate: int, path: str) -> None:
    """Write a NumPy float32 array to a 16-bit PCM WAV file."""
    pcm = (samples * 32767).astype(np.int16)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    print(f"Saved WAV file: {path}")


def play_local(samples: np.ndarray, sample_rate: int) -> None:
    """Play the tone on the local audio device."""
    import sounddevice as sd
    print("Playing … (you should NOT hear anything if your hearing is typical)")
    sd.play(samples, samplerate=sample_rate)
    sd.wait()
    print("Done.")


def send_to_home_assistant(
    samples: np.ndarray,
    sample_rate: int,
    ha_url: str,
    token: str,
    entity_id: str,
) -> None:
    """Upload the tone to Home Assistant and play it on a media player entity.

    Steps:
      1. Write WAV to an in-memory buffer.
      2. Upload to /api/media_player/browse_media or use a local www folder.
         (Here we save to the HA 'www' folder via the API, then call play_media.)
    """
    import requests

    # Build in-memory WAV
    buf = io.BytesIO()
    pcm = (samples * 32767).astype(np.int16)
    with wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    buf.seek(0)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    ha_url = ha_url.rstrip("/")

    # Option A – If HA can reach a local/network file, save the WAV and
    # reference it as /local/ultrasonic.wav (files in <config>/www/).
    # For simplicity we call play_media with a media_content_id pointing
    # to an externally-hosted or local URL.  Save the file first:
    wav_filename = "ultrasonic.wav"
    save_wav(samples, sample_rate, wav_filename)
    print(f"Place '{wav_filename}' in your Home Assistant <config>/www/ folder.")

    # Call the media_player.play_media service
    service_url = f"{ha_url}/api/services/media_player/play_media"
    payload = {
        "entity_id": entity_id,
        "media_content_id": f"/local/{wav_filename}",
        "media_content_type": "music",
    }

    print(f"Calling {service_url} for entity {entity_id} …")
    resp = requests.post(service_url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    print(f"Home Assistant responded: {resp.status_code}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ultrasonic tone generator")
    parser.add_argument("--save", metavar="FILE", help="Save WAV to FILE instead of playing")
    parser.add_argument("--ha-url", metavar="URL", help="Home Assistant base URL")
    parser.add_argument("--ha-token", metavar="TOKEN", help="HA long-lived access token")
    parser.add_argument("--entity", metavar="ID", help="HA media_player entity id")
    parser.add_argument("--freq", type=int, default=FREQUENCY_HZ, help="Frequency in Hz")
    parser.add_argument("--duration", type=float, default=DURATION_S, help="Duration in seconds")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    freq = args.freq
    duration = args.duration

    print(f"Generating {freq} Hz tone for {duration} seconds …")
    print(f"Sample rate : {SAMPLE_RATE} Hz")
    print(f"Amplitude   : {AMPLITUDE}")
    print()

    if freq >= SAMPLE_RATE / 2:
        raise ValueError(
            f"Frequency ({freq} Hz) must be below the Nyquist limit "
            f"({SAMPLE_RATE // 2} Hz). Increase SAMPLE_RATE."
        )

    tone = generate_tone(freq, duration, SAMPLE_RATE, AMPLITUDE)

    # Home Assistant mode
    if args.ha_url and args.ha_token and args.entity:
        send_to_home_assistant(tone, SAMPLE_RATE, args.ha_url, args.ha_token, args.entity)
        return

    # Save-only mode
    if args.save:
        save_wav(tone, SAMPLE_RATE, args.save)
        return

    # Default: local playback
    play_local(tone, SAMPLE_RATE)


if __name__ == "__main__":
    main()
