# Subleq Scramble

### Author: Shatterbox

Category: Reverse Engineering

Estimated Difficulty: Easy-Medium

Topics:

- Esoteric Programming Language (Subleq)
- Dynamic analysis
- Cellular Automaton (Langton's Ant)
- Data visualization (2D grid)
- Algorithm reversal

## Description:

Some dude's been trying to hide even more secrets behind yet another one of his "all-new, totally one-of-a-kind encryption algorithms" that he'd been yapping about.

Apparently it's some sort of "subleq emulator" that runs thousands of iterations of an image encryption algorithm...
before straight-up _memdumping_ the entire program state into a binary file when it's done.

_All of it._

Given that he was kind enough to send us an encrypted file, that probably means the algorithm's open-source now.

Nobody tell him.

- Flag format is specifically `/L3AK{[A-Z0-9?'_,]+}/`
