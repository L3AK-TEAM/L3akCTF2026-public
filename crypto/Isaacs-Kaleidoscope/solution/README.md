# Isaac's Kaleidoscope Solution
### Author: Suvoni

We are provided with a web-based GUI which performs a custom fractal encryption scheme. In this scheme, we can enter up to 200 characters and see some very colorfully rendered fractals which "encrypt" our message. Through some testing with various inputs, we can see that every 16 characters produces a new fractal image, leading us to the conclusion that every 16-bytes is independently encrypted into a fractal. We can also see that with no input, there are 4 fractal images, so we can conclude that the flag is likely being appended to our input before fractal encryption. Thus we essentially have fractal block cipher in ECB mode, which is susceptible to a chosen-prefix oracle attack (similar to AES ECB).

The challenge name plus the fractal images point toward Isaac Newton and Newton fractals. In Newton fractals, each color region in an image corresponds to a single root of a monic polynomial with complex coefficients. Since there are 8 basins (color regions) in every image, there are 8 roots, and we can reasonably guess that every 2 bytes of our input are used as a complex coefficient (although knowledge of the coefficients is not strictly necessary for the ECB oracle attack!). The important part of this is that the brightest points in each color region (we can see a "glint" spot in each one) correspond to the coordinates of that root, which are deterministic and unique to each 16-byte block.

The colors are randomized between renders, so direct PNG equality comparison is not useful, but the geometric structure of each fractal is the same (i.e., the same input renders the exact same fractal image aside from color of the basins). For a single image we can recover the polynomial roots as follows:

1. Decode the png
2. Convert RGB pixels to HSL
3. Cluster saturated pixels by hue to separate the eight basins
4. In each basin, average the brightest pixels to estimate the root location
5. Convert pixel coordinates back to complex-plane coordinates with the public viewport from `/api/challenge`
6. Compare the unordered set of eight estimated roots

For example, for byte zero, send 15 bytes of padding:

```text
AAAAAAAAAAAAAAA
```

The first rendered block is then:

```text
AAAAAAAAAAAAAAAL
```

where `L` is the first byte of the flag. We extract that block's root-set signature using the steps above.

Then we try candidate bytes as chosen input:

```text
AAAAAAAAAAAAAAAa
AAAAAAAAAAAAAAAb
...
AAAAAAAAAAAAAAAL
...
```

The correct candidate `AAAAAAAAAAAAAAAL` produces the same 16-byte block and therefore the same root set coordinates.

For later bytes, we shorten the prefix and include the bytes already recovered:

```text
AAAAAAAAAAAAAA + recovered + candidate
```

Continuing this method we recover the flag in due time (my solver takes ~50 minutes on the live remote, due to the large delay in image rendering).

Flag: ``L3AK{N3wT0N_fR4cT@Ls_Ar3_m4STerP1eC3s_0F_Ma7H_&_ArT}``
