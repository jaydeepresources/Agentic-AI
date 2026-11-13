import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
CHAT_COMPLETIONS_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_ID = "nvidia/nemotron-3.5-super-vl-120b-a12b"
SYSTEM_PROMPT = (
    "Write one complete story based on the user's phrase. "
    "Use no more than 100 words, give it a natural ending, and output only the story."
)


def generate_story(api_key: str, phrase: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": phrase},
    ]

    for attempt in range(2):
        request = Request(
            CHAT_COMPLETIONS_URL,
            data=json.dumps(
                {
                    "model": MODEL_ID,
                    "messages": messages,
                    "max_tokens": 1024,
                    "chat_template_kwargs": {"enable_thinking": False},
                    "stream": False,
                }
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=60) as response:
            payload = json.load(response)

        if not isinstance(payload, dict):
            raise ValueError("NVIDIA returned an unexpected chat response.")
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ValueError(
                f"NVIDIA returned no chat choices (response keys: {sorted(payload)})."
            )
        choice = choices[0]
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise ValueError("NVIDIA returned a malformed chat message.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            finish_reason = choice.get("finish_reason")
            raise ValueError(
                "NVIDIA returned no story text "
                f"(finish_reason={finish_reason!r}, message keys={sorted(message)})."
            )

        story = content.strip()
        if len(story.split()) <= 100:
            return story

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

    raise ValueError("NVIDIA did not return a story within the 100-word limit.")


def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)
    api_key = os.getenv("NVIDIA_AI_KEY") or os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print(
            "NVIDIA API key not found. Set NVIDIA_AI_KEY or NVIDIA_API_KEY "
            "in the project .env file.",
            file=sys.stderr,
        )
        return 1

    phrase = input("Enter a phrase for your story: ").strip()
    if not phrase:
        print("Please enter a non-empty phrase.", file=sys.stderr)
        return 1

    try:
        story = generate_story(api_key, phrase)
    except HTTPError as error:
        print(f"NVIDIA API returned HTTP {error.code}: {error.reason}", file=sys.stderr)
        return 1
    except URLError as error:
        print(f"Could not connect to NVIDIA API: {error.reason}", file=sys.stderr)
        return 1
    except TimeoutError:
        print("The request to NVIDIA API timed out.", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, ValueError) as error:
        print(f"Could not generate a story: {error}", file=sys.stderr)
        return 1

    print(f"\n{story}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
