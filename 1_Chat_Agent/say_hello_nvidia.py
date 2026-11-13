import json
import logging
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
CHAT_COMPLETIONS_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_ID = "nvidia/nemotron-3.5-super-vl-120b-a12b"
GREETING_PROMPT = "Say hello to me in one short sentence."


def send_greeting(api_key: str) -> str:
    request_body = {
        "model": MODEL_ID,
        "messages": [{"role": "user", "content": GREETING_PROMPT}],
        "max_tokens": 128,
        "stream": False,
    }
    request = Request(
        CHAT_COMPLETIONS_URL,
        data=json.dumps(request_body).encode("utf-8"),
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
        raise ValueError("NVIDIA returned no chat choices.")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("NVIDIA returned a malformed chat message.")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("NVIDIA returned an empty chat response.")
    return content.strip()


def main() -> int:
    logger.info("Step 1/5: Loading environment variables from %s.", ENV_PATH)
    load_dotenv(dotenv_path=ENV_PATH)

    logger.info("Step 2/5: Checking for an NVIDIA API key.")
    api_key = os.getenv("NVIDIA_AI_KEY") or os.getenv("NVIDIA_API_KEY")
    if not api_key:
        logger.error(
            "NVIDIA API key not found. Set NVIDIA_AI_KEY or NVIDIA_API_KEY "
            "in the project .env file."
        )
        return 1
    logger.info("NVIDIA API key found; its value will not be displayed.")

    logger.info("Step 3/5: Preparing a greeting request.")
    logger.info("Model: %s", MODEL_ID)
    logger.info("Prompt: %s", GREETING_PROMPT)
    logger.info(
        "This sends one request to NVIDIA; API charges or rate limits may apply."
    )
    try:
        confirmation = input("Send greeting request? [y/N]: ").strip().lower()
    except EOFError:
        logger.error("No console input is available; stopping before sending a request.")
        return 1

    if confirmation not in {"y", "yes"}:
        logger.info("Request cancelled. No chat request was sent.")
        return 0

    logger.info("Step 4/5: Sending the greeting request to NVIDIA.")
    try:
        reply = send_greeting(api_key)
    except HTTPError as error:
        logger.error("NVIDIA API returned HTTP %d: %s", error.code, error.reason)
        return 1
    except URLError as error:
        logger.error("Could not connect to NVIDIA API: %s", error.reason)
        return 1
    except TimeoutError:
        logger.error("The request to NVIDIA API timed out.")
        return 1
    except (json.JSONDecodeError, ValueError) as error:
        logger.error("Could not read NVIDIA chat response: %s", error)
        return 1

    logger.info("Step 5/5: Greeting received from %s.", MODEL_ID)
    print(f"\n{MODEL_ID}: {reply}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
