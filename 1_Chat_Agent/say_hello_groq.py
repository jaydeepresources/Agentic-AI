import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq, GroqError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def main() -> int:
    logger.info("Step 1/5: Loading environment variables from %s", ENV_PATH)
    load_dotenv(dotenv_path=ENV_PATH)
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("Groq")
    if not api_key:
        logger.error(
            "Groq API key not found. Set GROQ_API_KEY in the project .env file."
        )
        return 1
    logger.info("Groq API key found; its value will not be displayed.")

    logger.info("Step 2/5: Connecting to Groq and retrieving available model IDs.")
    client = Groq(api_key=api_key)
    try:
        models = client.models.list()
    except GroqError as error:
        logger.error(
            "Could not retrieve Groq models (%s): %s",
            type(error).__name__,
            error,
        )
        return 1

    model_ids = sorted(model.id for model in models.data)
    if not model_ids:
        logger.warning("Groq returned no models for this API key.")
        return 0

    logger.info("Step 3/5: Found %d model(s).", len(model_ids))
    logger.info(
        "The script will send one chat request to each model. "
        "Some models may not support chat; API charges or rate limits may apply."
    )
    try:
        confirmation = input("Continue? [y/N]: ").strip().lower()
    except EOFError:
        logger.error("No console input is available; stopping before sending requests.")
        return 1

    if confirmation not in {"y", "yes"}:
        logger.info("Request cancelled. No chat requests were sent.")
        return 0

    logger.info("Step 4/5: Sending a short greeting request to each model.")
    succeeded = 0
    failed = 0
    for index, model_id in enumerate(model_ids, start=1):
        logger.info("[%d/%d] Sending greeting to %s.", index, len(model_ids), model_id)
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "user",
                        "content": "Say hello to me in one short sentence.",
                    }
                ],
            )
        except GroqError as error:
            failed += 1
            logger.error(
                "[%d/%d] %s could not answer (%s): %s",
                index,
                len(model_ids),
                model_id,
                type(error).__name__,
                error,
            )
            continue

        if not response.choices:
            failed += 1
            logger.warning(
                "[%d/%d] %s returned no chat choices.",
                index,
                len(model_ids),
                model_id,
            )
            continue

        message = response.choices[0].message.content
        if message is None:
            failed += 1
            logger.warning(
                "[%d/%d] %s returned an empty response.",
                index,
                len(model_ids),
                model_id,
            )
            continue

        succeeded += 1
        logger.info("[%d/%d] %s replied: %s", index, len(model_ids), model_id, message)

    logger.info("Step 5/5: Finished testing all listed Groq models.")
    logger.info(
        "Summary: %d succeeded, %d failed, %d total.",
        succeeded,
        failed,
        len(model_ids),
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
