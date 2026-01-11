import os
from openai import OpenAI


def get_client() -> OpenAI:
    # OpenAI SDK automatically reads OPENAI_API_KEY from env,
    # but we do a quick sanity check for clearer errors.
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set in environment.")
    return OpenAI()
