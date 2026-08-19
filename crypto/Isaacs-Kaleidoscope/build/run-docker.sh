#!/bin/sh
set -eu

docker build -t isaacs-kaleidoscope-fractal-block .
docker run --rm -p 8767:8767 isaacs-kaleidoscope-fractal-block
