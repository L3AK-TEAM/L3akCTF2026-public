#!/usr/bin/env python3
import json

with open("answers.json") as file:
    answers = json.load(file)

questions = [
    ("What is the password of Natsume's Windows account?", "password"),
    ("What is the name of the malicious executable found on Natsume's machine?", "filename.exe"),
    ("What password did Natsume use to extract the tool sent by the attacker?", "password"),
    ("What is the master encryption key used by ModCollabTool?", "key"),
    ("What MITRE ATT&CK technique does ModCollabTool use? (obfuscation or encryption for impact)", "TXXXX"),
    ("What map contains the attacker's planted artifact? (evidence.7z password: s0und_0f_a_s0ul)", "mXX_XX_XX_XX"),
    (
        "The attacker planted something in Gwyn's boss room. Find the collision mesh ID, "
        "boss room BGM ThinkParamID, XYZ coordinates of the model, and the map piece ID.",
        "{mesh:XXXXXX|ThinkParamID:XXXXXX|pos:X,X,X|map:mXX_XX_XX_XX}",
    ),
]

for number, (question, answer_format) in enumerate(questions, 1):
    print(f"Q{number}) {question}")
    print(f"Format: {answer_format}\n")
    try:
        answer = input("Answer: ").strip()
    except EOFError:
        raise SystemExit
    expected = answers[str(number)]
    valid = expected if isinstance(expected, list) else [expected]
    if answer.casefold() not in {item.casefold() for item in valid}:
        print("Wrong answer!")
        raise SystemExit
    print("Correct!\n")

with open("flag.txt") as file:
    print(file.read().strip())
