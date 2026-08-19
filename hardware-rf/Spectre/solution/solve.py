import wave
from pathlib import Path
import numpy as np
from PIL import Image

def load_image(path):
    image = np.array(Image.open(path).convert("L"), dtype=np.float32) / 255
    low, high = np.percentile(image, [0.2, 99.85])
    if high > low:
        image = (image - low) / (high - low)
    return np.clip(image, 0, 1)

def get_magnitude(image):
    image = image[::-1]
    resized = Image.fromarray(np.round(image * 255).astype(np.uint8))
    resized = resized.resize((image.shape[1], 257), Image.Resampling.BICUBIC)
    spectrogram = np.array(resized, dtype=np.float32) / 255
    spectrogram = np.clip(spectrogram, 0, 1) ** 0.85

    magnitude = 10 ** ((-60 + 60 * spectrogram) / 20)
    magnitude[0] *= 0.05
    magnitude /= magnitude.max() + 1e-8
    return magnitude.astype(np.float32)

def make_frames(frame_count):
    length = (frame_count - 1) * 192 + 512
    starts = np.arange(frame_count)[:, None] * 192
    indexes = starts + np.arange(512)[None, :]
    window = np.hanning(512).astype(np.float32)
    normalization = np.zeros(length, dtype=np.float32)

    np.add.at(normalization, indexes.ravel(), np.tile(window ** 2, frame_count))
    normalization[normalization < 1e-8] = 1
    return indexes, window, normalization

def stft(audio, indexes, window):
    frames = audio[indexes] * window
    return np.fft.rfft(frames, n=512, axis=1).T

def istft(spectrogram, indexes, window, normalization):
    frames = np.fft.irfft(spectrogram.T, n=512, axis=1).real.astype(np.float32)
    frames *= window
    audio = np.zeros(len(normalization), dtype=np.float32)
    np.add.at(audio, indexes.ravel(), frames.ravel())
    return audio / normalization

def griffin_lim(magnitude):
    indexes, window, normalization = make_frames(magnitude.shape[1])
    random = np.random.default_rng(20260722)
    phase = np.exp(2j * np.pi * random.random(magnitude.shape)).astype(np.complex64)

    for iteration in range(240):
        audio = istft(magnitude * phase, indexes, window, normalization)
        rebuilt = stft(audio, indexes, window)
        phase = rebuilt / (np.abs(rebuilt) + 1e-8)

        if iteration == 0 or (iteration + 1) % 50 == 0:
            error = np.linalg.norm(np.abs(rebuilt) - magnitude) / np.linalg.norm(magnitude)
            print(f"Iteration {iteration + 1}/240, error: {error:.4f}", flush=True)

    audio = istft(magnitude * phase, indexes, window, normalization)
    audio -= audio.mean()
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio /= peak
    return audio

def save_wav(path, audio):
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = np.clip(audio * 0.92, -1, 1)
    samples = np.round(samples * 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(samples.tobytes())

def main():
    input_path = "dist/spectre.png"
    output_path = "output/spectre_griffinlim_best_guess.wav"
    image = load_image(input_path)
    magnitude = get_magnitude(image)
    audio = griffin_lim(magnitude)
    save_wav(output_path, audio)
    print(f"Saved {output_path}")

main()
