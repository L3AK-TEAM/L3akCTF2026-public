const crypto = require("crypto");

const DEFAULT_CONFIG = {
  blockSize: 16,
  coefficientsPerBlock: 8,
  polynomialDegree: 8,
  imageSize: 240,
  viewport: {
    centerX: 0,
    centerY: 0,
    scale: 28
  },
  maxIterations: 34,
  tolerance: 1e-6,
  coefficientOffset: 64,
  coefficientDivisor: 6,
  rootSolveIterations: 80,
  rootSolveTolerance: 1e-10,
  lightnessDither: 0.15
};

function mergeConfig(config) {
  const merged = Object.assign({}, DEFAULT_CONFIG, config || {});
  merged.viewport = Object.assign({}, DEFAULT_CONFIG.viewport, (config && config.viewport) || {});
  return merged;
}

function complexAdd(a, b) {
  return { re: a.re + b.re, im: a.im + b.im };
}

function complexSub(a, b) {
  return { re: a.re - b.re, im: a.im - b.im };
}

function complexMul(a, b) {
  return {
    re: a.re * b.re - a.im * b.im,
    im: a.re * b.im + a.im * b.re
  };
}

function complexDiv(a, b) {
  const denominator = b.re * b.re + b.im * b.im;
  return {
    re: (a.re * b.re + a.im * b.im) / denominator,
    im: (a.im * b.re - a.re * b.im) / denominator
  };
}

function complexScale(a, value) {
  return { re: a.re * value, im: a.im * value };
}

function complexAbs(a) {
  return Math.hypot(a.re, a.im);
}

function byteToCoord(byteValue, config) {
  const cfg = mergeConfig(config);
  return (byteValue - cfg.coefficientOffset) / cfg.coefficientDivisor;
}

function blockToCoefficients(block, config) {
  const cfg = mergeConfig(config);

  if (!Buffer.isBuffer(block) || block.length !== cfg.blockSize) {
    throw new Error(`blockToCoefficients expects exactly ${cfg.blockSize} bytes`);
  }

  const coefficients = [];
  for (let i = 0; i < cfg.blockSize; i += 2) {
    coefficients.push({
      re: byteToCoord(block[i], cfg),
      im: byteToCoord(block[i + 1], cfg)
    });
  }

  return coefficients;
}

function evaluateMonicPolynomial(z, coefficients) {
  let value = { re: 1, im: 0 };

  for (let i = coefficients.length - 1; i >= 0; i -= 1) {
    value = complexAdd(complexMul(value, z), coefficients[i]);
  }

  return value;
}

function evaluateMonicDerivative(z, coefficients) {
  const degree = coefficients.length;

  if (degree === 0) {
    return { re: 0, im: 0 };
  }

  let value = { re: degree, im: 0 };

  for (let exponent = degree - 1; exponent >= 1; exponent -= 1) {
    value = complexAdd(complexMul(value, z), complexScale(coefficients[exponent], exponent));
  }

  return value;
}

function polynomialRootBound(coefficients) {
  let maxCoefficient = 0;

  for (const coefficient of coefficients) {
    maxCoefficient = Math.max(maxCoefficient, complexAbs(coefficient));
  }

  return Math.max(1, 1 + maxCoefficient);
}

function polynomialRoots(coefficients, config) {
  const cfg = mergeConfig(config);
  const degree = coefficients.length;

  if (degree === 0) {
    return [];
  }

  if (degree === 1) {
    return [{ re: -coefficients[0].re, im: -coefficients[0].im }];
  }

  const radius = polynomialRootBound(coefficients);
  const roots = [];

  for (let i = 0; i < degree; i += 1) {
    const angle = (2 * Math.PI * (i + 0.5)) / degree;
    roots.push({
      re: radius * Math.cos(angle),
      im: radius * Math.sin(angle)
    });
  }

  for (let iteration = 0; iteration < cfg.rootSolveIterations; iteration += 1) {
    let maxDelta = 0;

    for (let i = 0; i < degree; i += 1) {
      let denominator = { re: 1, im: 0 };

      for (let j = 0; j < degree; j += 1) {
        if (i !== j) {
          denominator = complexMul(denominator, complexSub(roots[i], roots[j]));
        }
      }

      if (complexAbs(denominator) < 1e-24) {
        const nudge = 1e-8 * (i + 1);
        denominator = { re: denominator.re + nudge, im: denominator.im - nudge };
      }

      const delta = complexDiv(evaluateMonicPolynomial(roots[i], coefficients), denominator);
      roots[i] = complexSub(roots[i], delta);
      maxDelta = Math.max(maxDelta, complexAbs(delta));
    }

    if (maxDelta < cfg.rootSolveTolerance) {
      break;
    }
  }

  return roots;
}

function rootsToMonicCoefficients(roots) {
  let polynomial = [{ re: 1, im: 0 }];

  for (const rootValue of roots) {
    const next = Array.from({ length: polynomial.length + 1 }, function zero() {
      return { re: 0, im: 0 };
    });
    const negRoot = { re: -rootValue.re, im: -rootValue.im };

    for (let i = 0; i < polynomial.length; i += 1) {
      next[i] = complexAdd(next[i], complexMul(polynomial[i], negRoot));
      next[i + 1] = complexAdd(next[i + 1], polynomial[i]);
    }

    polynomial = next;
  }

  return polynomial.slice(0, Math.max(0, polynomial.length - 1));
}

function rootSeparation(roots) {
  let minimum = Infinity;

  for (let i = 0; i < roots.length; i += 1) {
    for (let j = i + 1; j < roots.length; j += 1) {
      minimum = Math.min(minimum, Math.hypot(roots[i].re - roots[j].re, roots[i].im - roots[j].im));
    }
  }

  return roots.length < 2 ? Infinity : minimum;
}

function mapPixelToComplex(x, y, width, height, config) {
  const cfg = mergeConfig(config);
  const aspect = width / height;
  const scaleX = cfg.viewport.scale * aspect;
  const scaleY = cfg.viewport.scale;
  return {
    re: cfg.viewport.centerX + (x / (width - 1) - 0.5) * scaleX,
    im: cfg.viewport.centerY + (0.5 - y / (height - 1)) * scaleY
  };
}

function mapComplexToPixel(z, width, height, config) {
  const cfg = mergeConfig(config);
  const aspect = width / height;
  const scaleX = cfg.viewport.scale * aspect;
  const scaleY = cfg.viewport.scale;
  return {
    x: ((z.re - cfg.viewport.centerX) / scaleX + 0.5) * (width - 1),
    y: (0.5 - (z.im - cfg.viewport.centerY) / scaleY) * (height - 1)
  };
}

function nearestRootIndex(re, im, roots) {
  let bestIndex = -1;
  let bestDistance = Infinity;

  for (let i = 0; i < roots.length; i += 1) {
    const dx = re - roots[i].re;
    const dy = im - roots[i].im;
    const distance = dx * dx + dy * dy;
    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = i;
    }
  }

  return bestIndex;
}

function iteratePoint(startRe, startIm, coefficients, roots, config) {
  const cfg = mergeConfig(config);
  const toleranceSquared = cfg.tolerance * cfg.tolerance;
  let zr = startRe;
  let zi = startIm;

  for (let iteration = 0; iteration < cfg.maxIterations; iteration += 1) {
    const rootIndex = nearestRootIndex(zr, zi, roots);
    if (rootIndex >= 0) {
      const dx = zr - roots[rootIndex].re;
      const dy = zi - roots[rootIndex].im;
      if (dx * dx + dy * dy <= toleranceSquared) {
        return { rootIndex, iterations: iteration, converged: true };
      }
    }

    const z = { re: zr, im: zi };
    const value = evaluateMonicPolynomial(z, coefficients);
    const derivative = evaluateMonicDerivative(z, coefficients);
    const denominator = derivative.re * derivative.re + derivative.im * derivative.im;

    if (denominator < 1e-24 || !Number.isFinite(denominator)) {
      break;
    }

    const step = complexDiv(value, derivative);
    zr -= step.re;
    zi -= step.im;

    if (!Number.isFinite(zr) || !Number.isFinite(zi)) {
      break;
    }
  }

  return {
    rootIndex: nearestRootIndex(zr, zi, roots),
    iterations: cfg.maxIterations,
    converged: false
  };
}

function hslToRgb(hue, saturation, lightness) {
  const s = saturation / 100;
  const l = lightness / 100;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const h = (((hue % 360) + 360) % 360) / 60;
  const x = c * (1 - Math.abs((h % 2) - 1));
  let r = 0;
  let g = 0;
  let b = 0;

  if (h >= 0 && h < 1) {
    r = c;
    g = x;
  } else if (h >= 1 && h < 2) {
    r = x;
    g = c;
  } else if (h >= 2 && h < 3) {
    g = c;
    b = x;
  } else if (h >= 3 && h < 4) {
    g = x;
    b = c;
  } else if (h >= 4 && h < 5) {
    r = x;
    b = c;
  } else {
    r = c;
    b = x;
  }

  const m = l - c / 2;
  return [
    Math.round((r + m) * 255),
    Math.round((g + m) * 255),
    Math.round((b + m) * 255)
  ];
}

function createRandom() {
  let state = crypto.randomBytes(4).readUInt32BE(0) || 1;

  return function nextRandom() {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    return ((state >>> 0) / 0x100000000);
  };
}

function shuffledRootHues(rootCount, random) {
  const slots = Array.from({ length: rootCount }, (_, index) => index);

  for (let i = slots.length - 1; i > 0; i -= 1) {
    const j = Math.floor(random() * (i + 1));
    const tmp = slots[i];
    slots[i] = slots[j];
    slots[j] = tmp;
  }

  const offset = random() * 360;
  const jitter = 360 / rootCount * 0.08;
  return slots.map((slot) => offset + slot * 360 / rootCount + (random() - 0.5) * jitter);
}

function renderImageData(coefficients, config) {
  const cfg = mergeConfig(config);
  const width = cfg.imageSize;
  const height = cfg.imageSize;
  const roots = polynomialRoots(coefficients, cfg);
  const data = new Uint8ClampedArray(width * height * 4);
  const random = createRandom();
  const hues = shuffledRootHues(roots.length, random);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const point = mapPixelToComplex(x, y, width, height, cfg);
      const result = iteratePoint(point.re, point.im, coefficients, roots, cfg);
      const offset = (y * width + x) * 4;

      if (result.rootIndex >= 0) {
        const progress = result.iterations / Math.max(1, cfg.maxIterations);
        const dither = (random() - 0.5) * cfg.lightnessDither;
        const lightness = Math.max(24, Math.min(67, 66 - progress * 38 + dither));
        const color = hslToRgb(hues[result.rootIndex], 74, lightness);
        data[offset] = color[0];
        data[offset + 1] = color[1];
        data[offset + 2] = color[2];
        data[offset + 3] = 255;
      } else {
        data[offset] = 5;
        data[offset + 1] = 6;
        data[offset + 2] = 8;
        data[offset + 3] = 255;
      }
    }
  }

  for (let rootIndex = 0; rootIndex < roots.length; rootIndex += 1) {
    const pixel = mapComplexToPixel(roots[rootIndex], width, height, cfg);
    const cx = Math.round(pixel.x);
    const cy = Math.round(pixel.y);

    for (let dy = -4; dy <= 4; dy += 1) {
      for (let dx = -4; dx <= 4; dx += 1) {
        const x = cx + dx;
        const y = cy + dy;
        const distance = (x - pixel.x) * (x - pixel.x) + (y - pixel.y) * (y - pixel.y);
        if (distance > 14) {
          continue;
        }
        if (x < 0 || x >= width || y < 0 || y >= height) {
          continue;
        }
        const lightness = Math.max(69, 84 - distance * 2.6);
        const color = hslToRgb(hues[rootIndex], 82, lightness);
        const offset = (y * width + x) * 4;
        data[offset] = color[0];
        data[offset + 1] = color[1];
        data[offset + 2] = color[2];
        data[offset + 3] = 255;
      }
    }
  }

  return data;
}

module.exports = {
  DEFAULT_CONFIG,
  mergeConfig,
  byteToCoord,
  blockToCoefficients,
  complexAdd,
  complexSub,
  complexMul,
  complexDiv,
  complexAbs,
  evaluateMonicPolynomial,
  evaluateMonicDerivative,
  polynomialRoots,
  rootsToMonicCoefficients,
  rootSeparation,
  mapPixelToComplex,
  mapComplexToPixel,
  renderImageData
};
