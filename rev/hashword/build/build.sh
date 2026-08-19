set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

OUTPUT="hashword/hashword"
REGEN_PUZZLE=0
GARBLE=0
FLAG=""
HINT=""
POSITIONAL=()

die() { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }
step() { printf '\033[36m==>\033[0m %s\n' "$*"; }

usage() { sed -n '2,/^$/s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"; exit "${1:-0}"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        -o|--output)       [[ $# -ge 2 ]] || die "$1 needs a value"; OUTPUT="$2"; shift 2 ;;
        -p|--regen-puzzle) REGEN_PUZZLE=1; shift ;;
        -g|--garble)       GARBLE=1; shift ;;
        -h|--help)         usage 0 ;;
        --)                shift; break ;;
        -*)                die "unknown option: $1" ;;
        *)                 POSITIONAL+=("$1"); shift ;;
    esac
done
POSITIONAL+=("$@")

case "${#POSITIONAL[@]}" in
    0) printf 'no flag given\n\n' >&2; usage 1 >&2 ;;
    1) printf 'no hint URL given\n\n' >&2; usage 1 >&2 ;;
    2) FLAG="${POSITIONAL[0]}"; HINT="${POSITIONAL[1]}" ;;
    *) die "expected a flag and a hint URL, got ${#POSITIONAL[@]} arguments" ;;
esac

[[ -n "$FLAG" ]] || die "the flag is empty"
[[ -n "$HINT" ]] || die "the hint URL is empty"

command -v go >/dev/null || die "go is not on PATH"
if [[ $GARBLE -eq 1 ]]; then
    command -v garble >/dev/null || die "garble is not on PATH"
fi


step "checking the two generators agree on the board"
FP_PUZZLE="$(cd gen/genpuzzle && go run . -fingerprint)"
FP_FLAG="$(cd gen/genflag && go run . -fingerprint)"

if [[ "$FP_PUZZLE" != "$FP_FLAG" ]]; then
    die "board mismatch: genpuzzle has $FP_PUZZLE, genflag has $FP_FLAG
       the solution arrays in gen/genpuzzle/main.go and gen/genflag/main.go
       have drifted apart; make them identical before building"
fi
printf '    board %s\n' "$FP_PUZZLE"

if [[ $REGEN_PUZZLE -eq 1 ]]; then
    step "regenerating hashword/puzzle.go"
    (cd gen/genpuzzle && go run . -out ../../hashword/puzzle.go)
fi

step "sealing the flag into hashword/flag.go"
(cd gen/genflag && go run . -flag "$FLAG" -hint "$HINT" -out ../../hashword/flag.go)

step "building $OUTPUT"
OUT_ABS="$(cd "$(dirname "$OUTPUT")" && pwd)/$(basename "$OUTPUT")"
if [[ $GARBLE -eq 1 ]]; then
    (cd hashword && garble -tiny build -trimpath -o "$OUT_ABS" .)
else
    (cd hashword && go build -trimpath -ldflags='-s -w' -o "$OUT_ABS" .)
fi

step "done"
printf '    %s (%s)\n' "$OUTPUT" "$(du -h "$OUTPUT" | cut -f1)"


if command -v nm >/dev/null && [[ "$(nm "$OUTPUT" 2>/dev/null | wc -l)" -gt 0 ]]; then
    printf '\033[33mwarning:\033[0m %s still has a readable symbol table\n' "$OUTPUT" >&2
fi
