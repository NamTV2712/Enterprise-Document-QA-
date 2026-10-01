"""Public corpus metadata routes."""

from collections.abc import Callable, Sequence

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool


def create_corpus_router(
    load_supported_tickers: Callable[[], list[str]],
    supported_sections: Sequence[str],
) -> APIRouter:
    router = APIRouter()

    @router.get("/supported-tickers")
    async def supported_tickers() -> dict:
        """List of supported tickers — helps the UI/user know what they can ask about."""
        tickers = await run_in_threadpool(load_supported_tickers)
        return {
            "tickers": tickers,
            "sections": supported_sections,
        }

    return router
