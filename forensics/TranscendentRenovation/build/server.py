import sys
import time
from secret import FLAG

questions = [
    "1. What file format is a Jump List stored in? (`Format: *** **`)",
    "2. Which automaticDestinations file contains the `NoNeedToWonder` entry? (`Format: ****************.*********************-**`)",
    r"3. What share path is found in the file? (`Format: \\********\************`)",
    "4. Which stream holds the `NoNeedToWonder` rename data?",
    "5. What is the File Droid GUID for `NoNeedToWonder?",
    "6. What hostname is associated with this entry?",
    "7. What was the original name of the folder?",
]

answers = [
    "OLE CF",
    "f01b4d95cf55d32a.automaticDestinations-ms ",
    r"\\tsclient\HauntedHouse",
    "46",
    "ec2ab952-7e4d-11f1-89ad-a2dead7852ad",
    "logging-vm",
    "SoulSearching",
]

def normalize(s):
    return s.strip().lower()

def send_msg(msg):
    print(msg, end='', flush=True)

def rate_limiter():
    timestamps = []

    def is_allowed():
        nonlocal timestamps
        now = time.time()
        timestamps = [t for t in timestamps if now - t < 60]
        if len(timestamps) < 15:
            timestamps.append(now)
            return True
        return False

    return is_allowed

def handle_client():
    limiter = rate_limiter()
    answered = [False] * len(questions)
    
    send_msg("Welcome to the Ghost Hunt Terminal. Answer all questions to reveal the final flag.\nType 'exit' at any prompt to quit.\n\n")
    
    while not all(answered):
        if not limiter():
            send_msg("\n⚠ You're going too fast. Please wait a moment.\n")
            time.sleep(2)
            continue
        
        try:
            # Show unanswered
            send_msg("\nUnanswered Questions:\n")
            for i, (q, a) in enumerate(zip(questions, answered)):
                if not a:
                    send_msg(f"  {q}\n")
            
            # Show answered
            send_msg("\nAnswered so far:\n")
            for i, (q, a) in enumerate(zip(questions, answered)):
                if a:
                    send_msg(f"  ✅ {i+1}. {questions[i]} → {answers[i]}\n")
            
            send_msg("\nEnter question number to answer: ")
            qnum = input().strip()
            if not qnum or qnum.lower() == 'exit':
                send_msg("Goodbye!\n")
                break
            
            q_index = int(qnum) - 1
            if not (0 <= q_index < len(questions)):
                send_msg("Invalid question number.\n")
                continue
            if answered[q_index]:
                send_msg("That question is already answered.\n")
                continue
            
            send_msg("Enter your answer: ")
            user_answer = input().strip()
            if not user_answer or user_answer.lower() == 'exit':
                send_msg("Goodbye!\n")
                break
            
            if normalize(user_answer) == normalize(answers[q_index]):
                answered[q_index] = True
                send_msg("\n✔ Correct!\n")
            else:
                send_msg("\n✖ Incorrect, try again.\n")
        
        except (ValueError, EOFError, KeyboardInterrupt):
            break
    
    if all(answered):
        send_msg(f"\n🎉 All questions answered! Final flag:\n{FLAG}\n")

def main():
    handle_client()

if __name__ == "__main__":
    main()
