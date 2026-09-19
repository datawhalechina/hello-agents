import asyncio
import logging
from typing import AsyncGenerator, Generator, TypeVar, Any

T = TypeVar("T")
logger = logging.getLogger(__name__)

async def async_generator_wrapper(gen):
    """
    Wrap a synchronous generator into an asynchronous one.
    Also handles async generators transparently.
    """
    if hasattr(gen, '__aiter__'):
        async for item in gen:
            yield item
        return

    while True:
        try:
            # We must use run_in_executor because next() on sync generator blocks
            # But await asyncio.to_thread(next, sync_gen) is cleaner in Py3.9+
            # However, if sync_gen raises StopIteration, to_thread might wrap it in execution error or not propagate correctly
            # Let's be explicit
            
            def _next():
                try:
                    return next(gen)
                except StopIteration:
                    return StopIteration
                except Exception as e:
                    return e

            chunk = await asyncio.to_thread(_next)
            
            if chunk is StopIteration:
                break
            if isinstance(chunk, Exception):
                logger.error(f"Error in generator: {chunk}")
                break
                
            yield chunk
            
        except Exception as e:
            logger.error(f"Error in async_wrapper loop: {e}")
            break
