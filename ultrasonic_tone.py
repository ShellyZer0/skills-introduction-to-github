"""
Generate an ultrasonic tone above the human hearing range.

Human hearing typically ranges from 20 Hz to 20,000 Hz (20 kHz).
This script generates a sine wave at a frequency above 20 kHz,
which is inaudible to humans but can be emitted by speakers that
support the frequency (many smart speakers have tweeters capable
of reproducing frequencies up to ~24 kHz or higher).

Requirements:
    pip install numpy sounddevice

Usage:
    python ultrasonic_tone.py
"""

import numpy as np
import sounddevice as sd

# --- Configuration ---
FREQUENCY_HZ = 22000      # 22 kHz – above the ~20 kHz human hearing ceiling
DURATION_S = 5             # play for 5 seconds
SAMPLE_RATE = 48000        # samples per second (must be > 2x frequency per Nyquist)
AMPLITUDE = 0.8            # 0.0 – 1.0 (fraction of full scale)

def generate_tone(freq: float, duration: float, sample_rate: int, amplitude: float) -> np.ndarray:
    """Return a NumPy array containing a pure sine-wave tone."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)

def main() -> None:
    print(f"Generating {FREQUENCY_HZ} Hz tone for {DURATION_S} seconds …")
    print(f"Sample rate : {SAMPLE_RATE} Hz")
    print(f"Amplitude   : {AMPLITUDE}")
    print()

    if FREQUENCY_HZ >= SAMPLE_RATE / 2:
        raise ValueError(
            f"Frequency ({FREQUENCY_HZ} Hz) must be below the Nyquist limit "
            f"({SAMPLE_RATE // 2} Hz). Increase SAMPLE_RATE."
        )

    tone = generate_tone(FREQUENCY_HZ, DURATION_S, SAMPLE_RATE, AMPLITUDE)

    print("Playing … (you should NOT hear anything if your hearing is typical)")
    sd.play(tone, samplerate=SAMPLE_RATE)
    sd.wait()  # block until playback finishes
    print("Done.")

if __name__ == "__main__":
    main()
