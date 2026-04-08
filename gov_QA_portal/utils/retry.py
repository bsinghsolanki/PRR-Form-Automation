import time
import functools
from typing import Tuple, Type
from utils.logger import get_logger

log = get_logger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_failure: str = "skip"   # "skip" | "raise"
):
    """
    Decorator that retries a function on failure.

    Args:
        max_attempts : Total number of attempts (including first try)
        delay        : Initial wait in seconds between attempts
        backoff      : Multiplier applied to delay after each failure
                       e.g. delay=2, backoff=2 → waits 2s, 4s, 8s …
        exceptions   : Tuple of exception types to catch & retry on
        on_failure   : What to do after all attempts fail:
                         "skip"  → log error, return None (keeps loop alive)
                         "raise" → re-raise the last exception

    Usage:
        from utils.retry import retry

        @retry(max_attempts=3, delay=2, exceptions=(TimeoutException,))
        def click_tile(driver):
            ...

        @retry(max_attempts=3, delay=2, on_failure="raise")
        def critical_step():
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt      = 1
            current_delay = delay

            while attempt <= max_attempts:
                try:
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        log.info(
                            f"✅ '{func.__name__}' succeeded on attempt {attempt}"
                        )
                    return result

                except exceptions as e:
                    log.warning(
                        f"⚠️  '{func.__name__}' failed "
                        f"(attempt {attempt}/{max_attempts}) → {e}"
                    )

                    if attempt == max_attempts:
                        log.error(
                            f"❌ '{func.__name__}' failed after "
                            f"{max_attempts} attempts."
                        )
                        if on_failure == "raise":
                            raise
                        return None  # "skip" mode — caller handles None

                    log.info(
                        f"⏳ Retrying '{func.__name__}' "
                        f"in {current_delay:.1f}s …"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1

        return wrapper
    return decorator


def retry_step(func, *args, max_attempts=3, delay=2.0, **kwargs):
    """
    Functional (non-decorator) version of retry.
    Useful when you want to retry a lambda or inline call.

    Usage:
        result = retry_step(
            driver.find_element, By.XPATH, TILE_XPATH,
            max_attempts=3, delay=2
        )
    """
    attempt       = 1
    current_delay = delay

    while attempt <= max_attempts:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log.warning(
                f"⚠️  Step failed (attempt {attempt}/{max_attempts}) → {e}"
            )
            if attempt == max_attempts:
                log.error(f"❌ Step failed after {max_attempts} attempts.")
                raise
            log.info(f"⏳ Retrying in {current_delay:.1f}s …")
            time.sleep(current_delay)
            current_delay *= delay
            attempt += 1