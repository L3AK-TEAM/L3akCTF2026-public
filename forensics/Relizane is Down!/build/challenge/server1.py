import hashlib
import hmac
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# Operational limits remain hardcoded.
MAX_INCORRECT_ATTEMPTS = 4
MAX_ANSWER_LENGTH = 4096

# Load questions.json from the same directory as this script.
SCRIPT_DIRECTORY = Path(__file__).resolve().parent
QUESTIONS_FILE = SCRIPT_DIRECTORY / "questions.json"


def normalize_answer(answer: str) -> str:
    """
    Normalize an answer before hashing and comparison.

    Comparison is:
    - case-insensitive;
    - insensitive to leading/trailing whitespace;
    - insensitive to repeated whitespace;
    - Unicode-normalized.
    """
    normalized = unicodedata.normalize("NFKC", answer)

    # Remove surrounding whitespace and collapse repeated whitespace.
    normalized = " ".join(normalized.strip().split())

    # Unicode-aware case-insensitive normalization.
    return normalized.casefold()


def hash_answer(answer: str) -> str:
    """Normalize an answer and return its SHA-256 hash."""
    normalized = normalize_answer(answer)

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def load_challenge(
    file_path: Path,
) -> tuple[
    str,
    str,
    str,
    list[str],
    list[dict[str, Any]],
]:
    """
    Load and validate the challenge configuration.

    Returns:
        challenge_name,
        author,
        flag,
        notes,
        validated_questions
    """
    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Invalid challenge configuration")

    challenge_name = data.get("challenge_name")
    author = data.get("author")
    flag = data.get("flag")
    notes = data.get("notes", [])
    questions = data.get("questions")

    if (
        not isinstance(challenge_name, str)
        or not challenge_name.strip()
    ):
        raise ValueError("Invalid challenge configuration")

    if not isinstance(author, str) or not author.strip():
        raise ValueError("Invalid challenge configuration")

    if not isinstance(flag, str) or not flag.strip():
        raise ValueError("Invalid challenge configuration")

    if not isinstance(notes, list):
        raise ValueError("Invalid challenge configuration")

    if not isinstance(questions, list) or not questions:
        raise ValueError("Invalid challenge configuration")

    validated_notes: list[str] = []

    for note in notes:
        if not isinstance(note, str) or not note.strip():
            raise ValueError("Invalid challenge configuration")

        validated_notes.append(note.strip())

    validated_questions: list[dict[str, Any]] = []

    for item in questions:
        if not isinstance(item, dict):
            raise ValueError("Invalid challenge configuration")

        question = item.get("question")
        answer = item.get("answer")
        placeholder = item.get("placeholder")
        hint = item.get("hint")

        if not isinstance(question, str) or not question.strip():
            raise ValueError("Invalid challenge configuration")

        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Invalid challenge configuration")

        if (
            placeholder is not None
            and not isinstance(placeholder, str)
        ):
            raise ValueError("Invalid challenge configuration")

        if hint is not None and not isinstance(hint, str):
            raise ValueError("Invalid challenge configuration")

        validated_questions.append(
            {
                "question": question.strip(),
                "answer_hash": hash_answer(answer),
                "placeholder": (
                    placeholder.strip()
                    if isinstance(placeholder, str)
                    and placeholder.strip()
                    else None
                ),
                "hint": (
                    hint.strip()
                    if isinstance(hint, str)
                    and hint.strip()
                    else None
                ),
            }
        )

    return (
        challenge_name.strip(),
        author.strip(),
        flag.strip(),
        validated_notes,
        validated_questions,
    )


def read_answer() -> str | None:
    """
    Read one answer while enforcing the maximum input length.

    Returns None when:
    - the client disconnects;
    - the answer exceeds the configured limit.
    """
    # Read slightly beyond the limit so oversized input can be detected.
    raw_answer = sys.stdin.readline(MAX_ANSWER_LENGTH + 3)

    if raw_answer == "":
        # EOF: client disconnected.
        return None

    # Remove only CR/LF line-ending characters.
    answer = raw_answer.rstrip("\r\n")

    if len(answer) > MAX_ANSWER_LENGTH:
        print(
            f"{RED}✘ Answer is too long. "
            f"Connection closed.{RESET}",
            flush=True,
        )
        return None

    return answer


def print_banner(
    challenge_name: str,
    author: str,
    notes: list[str],
) -> None:
    """Print the challenge banner and configured notes."""
    separator = "-" * 50

    print(
        f"\n{separator} "
        f"{challenge_name} "
        f"{separator}\n"
    )

    print(
        f"{separator} "
        f"Author: {author} "
        f"{separator}\n"
    )

    for index, note in enumerate(notes, start=1):
        print(
            f"{BLUE}*** NOTE {index}: "
            f"{note}{RESET}\n"
        )


def run_challenge(
    questions: list[dict[str, Any]],
    flag: str,
) -> None:
    """Run the interactive challenge session."""
    total_questions = len(questions)

    for index, item in enumerate(questions, start=1):
        incorrect_count = 0

        while True:
            print(
                f"\n{BLUE}--- Question "
                f"{index}/{total_questions} ---{RESET}"
            )

            print(item["question"])

            if item["placeholder"]:
                print(
                    f"{YELLOW}format: "
                    f"{item['placeholder']}{RESET}"
                )

            print(">> ", end="", flush=True)

            user_answer = read_answer()

            if user_answer is None:
                return

            user_answer_hash = hash_answer(user_answer)

            if hmac.compare_digest(
                user_answer_hash,
                item["answer_hash"],
            ):
                print(
                    f"{GREEN}✔ Correct! Moving to the "
                    f"next question.{RESET}\n"
                )
                break

            incorrect_count += 1
            attempts_left = (
                MAX_INCORRECT_ATTEMPTS - incorrect_count
            )

            if attempts_left <= 0:
                print(
                    f"{RED}✘ Too many incorrect attempts. "
                    f"Exiting ...{RESET}\n",
                    flush=True,
                )
                return

            print(
                f"{RED}✘ Incorrect. You have "
                f"{attempts_left} attempt(s) left."
                f"{RESET}"
            )

            if item["hint"]:
                print(
                    f"{YELLOW}Hint: "
                    f"{item['hint']}{RESET}"
                )

    print(
        f"\n{GREEN}✔ You have successfully answered "
        f"all the questions!{RESET}\n"
    )

    print(
        f"{YELLOW}🏁 Here is your flag: "
        f"{flag}{RESET}\n",
        flush=True,
    )


def main() -> None:
    try:
        (
            challenge_name,
            author,
            flag,
            notes,
            questions,
        ) = load_challenge(QUESTIONS_FILE)

        print_banner(
            challenge_name,
            author,
            notes,
        )

        run_challenge(
            questions,
            flag,
        )

    except (EOFError, KeyboardInterrupt, BrokenPipeError):
        # Normal client disconnection or interrupted session.
        return

    except Exception:
        # Do not disclose exception details or tracebacks to players.
        print(
            f"{RED}The challenge service encountered "
            f"an error.{RESET}",
            flush=True,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()