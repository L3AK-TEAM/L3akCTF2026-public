// ...

function encrypt(userInput) {
  const plaintext = Buffer.concat([
    Buffer.from(userInput, "utf8"),
    secretFlag()
  ]);

  const padded = pkcs7Pad(plaintext, 16);
  const blocks = splitBlocks(padded, 16);

  return blocks.map((block) => {
    const coefficients = blockToCoefficients(block);
    return renderFractal(coefficients);
  });
}

// ...
