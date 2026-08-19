# Spectre Solution
### Author: Suvoni

We are given only a long, thin grayscale image named `spectre.png`. The challenge description states that the author says the flag out loud character by character, so the natural first guess is that the PNG is a rendered magnitude spectrogram of that recording. Inspecting the PNG dimensions we find that it's `4494 x 192`. There are 107 individual spectrogram "chunks" separated by dark vertical gaps, indicating a 107-character flag. We aren't given information like the duration of the audio recording, FFT window size, sample rate, etc., so we will have to guess these parameters.

After doing some research on reversing spectrograms back to audio, we find that a normal spectrogram image does not contain phase. Therefore, we cannot directly invert it with an inverse FFT - we need to estimate a phase that is consistent with the visible magnitude image. The [Griffin-Lim Algorithm](https://courses.grainger.illinois.edu/ece417/fa2023/slides/lec06.pdf) is the standard way to do that.

The provided solver normalizes the image, resizes the frequency axis to `n_fft // 2 + 1`, maps grayscale intensity to magnitude with a 60 dB range, then runs Griffin-Lim.

The resulting parameters that give the cleanest audio were:
```text
sample_rate = 16000
n_fft = 512
hop = 192
db_range = 60
gamma = 0.85
iterations = 240
flip = true
```

This produces a WAV around 54 seconds long which is audible enough to hear the flag!

Flag: `L3AK{5pectr3s_0f_the_fr3quency_re4lm_r3m41n_w1thin_the_5p3c7rogr4m_leav1ng_gh057ly_trac35_of_wh4t_0nc3_w4s}`
