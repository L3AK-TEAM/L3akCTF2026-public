# Lossy QR Solution
### Author: kyc

Since decoding returns all objects, it is sufficient to use a QR code that
has a smaller QR code inside it. Since we can enter arbitrary data, this
challenge is mainly an exercise in constructing data such that it decodes
into the smaller QR code shape. There are many tutorials for QR code encoding,
such as [1].

The main difficulty is that there are 8 possible mask patterns, and the official
spec uses the mask pattern that minimizes a penalty score for "bad" shapes
in the final code [2]. Having a small QR code is a very bad shape. So we must
also include data in the large QR code such that when the large QR code is
masked with any of the other mask patterns, the penalty score is even worse.

[1] https://www.thonky.com/qr-code-tutorial/introduction

[2] https://www.thonky.com/qr-code-tutorial/data-masking#choose-the-lowest-penalty-score-for-the-eight-mask-patterns

Flag: `L3AK{what_ab0ut_w1th_med1um_3rr0r_correction?}`
