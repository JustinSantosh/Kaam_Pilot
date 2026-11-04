"""The only module that knows which LLM vendor is in use (D-014)."""

import asyncio
from functools import lru_cache
from typing import Any, TypeVar

from langchain.chat_models import init_chat_model
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel, ValidationError

from app.config import get_settings

MAX_ATTEMPTS = 3
RETRYABLE_ERRORS = (OutputParserException, ValidationError, TimeoutError, ConnectionError)
RETRYABLE_ERROR_NAMES = {
    "APITimeoutError",
    "InternalServerError",
    "RateLimitError",
    "ServiceUnavailableError",
}
ResultT = TypeVar("ResultT")


class LLMNotConfiguredError(RuntimeError):
    pass


class LLMUnavailableError(RuntimeError):
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
    """Return a model bound to the extraction-only response schema."""
    return get_model().with_structured_output(schema)


async def invoke(
    runnable: Runnable[Any, ResultT],
    value: Any,
    *,
    config: RunnableConfig | None = None,
) -> ResultT:
    """Retry transient provider/structured-output failures within one bounded call budget."""
    timeout = get_settings().llm_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            for attempt in range(MAX_ATTEMPTS):
                try:
                    return await runnable.ainvoke(value, config=config)
                except Exception as exc:
                    status_code = getattr(exc, "status_code", None)
                    retryable = (
                        isinstance(exc, RETRYABLE_ERRORS)
                        or type(exc).__name__ in RETRYABLE_ERROR_NAMES
                        or status_code in {408, 429, 500, 502, 503, 504}
                    )
                    if not retryable or attempt == MAX_ATTEMPTS - 1:
                        raise LLMUnavailableError(
                            f"LLM request failed ({type(exc).__name__})"
                        ) from exc
                    await asyncio.sleep(0.25 * (2**attempt))
    except TimeoutError as exc:
        raise LLMUnavailableError("LLM request timed out") from exc
    raise LLMUnavailableError("LLM request exhausted retries")
