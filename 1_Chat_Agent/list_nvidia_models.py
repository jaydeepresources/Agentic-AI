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
MODELS_URL = "https://integrate.api.nvidia.com/v1/models"


def fetch_model_ids(api_key: str) -> list[str]:
    request = Request(
        MODELS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("NVIDIA returned an unexpected model-list response.")

    model_ids = {
        model["id"]
        for model in payload["data"]
        if isinstance(model, dict) and isinstance(model.get("id"), str)
    }
    return sorted(model_ids)


def main() -> int:
    logger.info("Step 1/3: Loading environment variables from %s", ENV_PATH)
    load_dotenv(dotenv_path=ENV_PATH)
    api_key = os.getenv("NVIDIA_AI_KEY") or os.getenv("NVIDIA_API_KEY")
    if not api_key:
        logger.error(
            "NVIDIA API key not found. Set NVIDIA_AI_KEY in the project .env file."
        )
        return 1
    logger.info("NVIDIA API key found; its value will not be displayed.")

    logger.info("Step 2/3: Requesting available model IDs from NVIDIA.")
    try:
        model_ids = fetch_model_ids(api_key)
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
        logger.error("Could not read NVIDIA model list: %s", error)
        return 1

    logger.info("Step 3/3: Displaying models.")
    if not model_ids:
        logger.warning("NVIDIA returned no model IDs for this API key.")
        return 0

    for model_id in model_ids:
        print(f"- {model_id}")
    print(f"\nTotal models found: {len(model_ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
