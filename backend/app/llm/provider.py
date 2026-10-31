"""The only module that knows which LLM vendor is in use (D-014)."""

from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from pydantic import BaseModel, ValidationError

from app.config import get_settings

MAX_ATTEMPTS = 3


class LLMNotConfiguredError(RuntimeError):
    pass


@lru_cache
def get_model() -> BaseChatModel:
    model = get_settings().llm_model
    if not model:
        raise LLMNotConfiguredError(
            "KP_LLM_MODEL is not set; use '<provider>:<model>', e.g. 'openai:<model-name>'"
        )
    return init_chat_model(model, temperature=0)


def structured(schema: type[BaseModel]) -> Runnable:
    """Model bound to `schema`, retried when the output doesn't parse or validate."""
    return (
        get_model()
        .with_structured_output(schema)
        .with_retry(
            retry_if_exception_type=(OutputParserException, ValidationError),
            stop_after_attempt=MAX_ATTEMPTS,
        )
    )
