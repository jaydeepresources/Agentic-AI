import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq, GroqError


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
MODEL_ID = "openai/gpt-oss-120b"
SYSTEM_PROMPT = (
    "Write one complete story based on the user's phrase. "
    "Use no more than 100 words, give it a natural ending, and output only the story."
)


def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("Groq")
    if not api_key:
        print(
            "Groq API key not found. Set GROQ_API_KEY in the project .env file.",
            file=sys.stderr,
        )
        return 1

    phrase = input("Enter a phrase for your story: ").strip()
    if not phrase:
        print("Please enter a non-empty phrase.", file=sys.stderr)
        return 1

    client = Groq(api_key=api_key)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": phrase},
    ]

    try:
        for attempt in range(2):
            response = client.chat.completions.create(
                model=MODEL_ID,
                messages=messages,
                max_completion_tokens=1024,
                include_reasoning=False,
            )
            if not response.choices:
                raise ValueError("Groq returned no chat choices.")

            choice = response.choices[0]
            content = choice.message.content
            if not isinstance(content, str) or not content.strip():
                refusal = getattr(choice.message, "refusal", None)
                details = f"finish_reason={choice.finish_reason!r}"
                if refusal:
                    details += f", refusal={refusal!r}"
                raise ValueError(f"Groq returned no story text ({details}).")

            story = content.strip()
            if len(story.split()) <= 100:
                print(f"\n{story}")
                return 0

            if attempt == 0:
                messages.extend(
                    [
                        {"role": "assistant", "content": story},
                        {
                            "role": "user",
                            "content": (
                                "Rewrite this as a complete story of at most 100 "
                                "words with a natural ending. Output only the story."
                            ),
                        },
                    ]
                )
    except (GroqError, ValueError) as error:
        print(f"Could not generate a story: {error}", file=sys.stderr)
        return 1

    print("Groq did not return a story within the 100-word limit.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
