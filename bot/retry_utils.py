import asyncio
import functools
import logging
import random

logger = logging.getLogger(__name__)


def async_retry(func=None, max_retries=3, base_delay=1, backoff_factor=2, jitter=0.1):
    """Decorator for async functions with exponential backoff and jitter.

    Can be used with or without arguments:
        @async_retry
        async def foo(): ...

        @async_retry(max_retries=5, base_delay=2)
        async def bar(): ...
    """
    if func is not None:
        return _async_retry_decorator(func, max_retries, base_delay, backoff_factor, jitter)
    else:
        def decorator(f):
            return _async_retry_decorator(f, max_retries, base_delay, backoff_factor, jitter)
        return decorator


def _async_retry_decorator(func, max_retries, base_delay, backoff_factor, jitter):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    delay = base_delay * (backoff_factor ** attempt)
                    delay_with_jitter = delay * (1 + random.uniform(-jitter, jitter))
                    logger.info(
                        "Attempt %d/%d failed (%s: %s). Retrying in %.2fs...",
                        attempt + 1, max_retries + 1, type(e).__name__, e, delay_with_jitter
                    )
                    await asyncio.sleep(delay_with_jitter)
        raise last_exception
    return wrapper
