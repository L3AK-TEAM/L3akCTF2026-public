#!/usr/bin/env python3
"""Intended solution: for each game, plot every square the WHITE queen moves to."""
import sys
import chess
import chess.pgn

path = sys.argv[1] if len(sys.argv) > 1 else "games.pgn"
grids = []
with open(path) as f:
    while True:
        game = chess.pgn.read_game(f)
        if game is None:
            break
        board = game.board()
        hits = set()
        for mv in game.mainline_moves():
            pc = board.piece_at(mv.from_square)
            if pc and pc.color == chess.WHITE and pc.piece_type == chess.QUEEN:
                hits.add(mv.to_square)
            board.push(mv)
        grid = []
        for rank in range(7, -1, -1):                     # rank 8 on top
            grid.append("".join(
                "#" if chess.square(file, rank) in hits else "."
                for file in range(8)))
        grids.append(grid)

# print grids side by side, 8 per row
for start in range(0, len(grids), 8):
    chunk = grids[start:start + 8]
    for r in range(8):
        print("   ".join(g[r] for g in chunk))
    print()
