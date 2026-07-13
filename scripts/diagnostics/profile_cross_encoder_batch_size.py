"""Measure CrossEncoder.predict latency for different batch sizes.

This script uses the same ten real candidate pairs as the warm-up profiler and
does not call any LLM provider. It checks whether explicitly setting batch_size
helps CPU inference for candidate_pool=10.
"""

from __future__ import annotations

import inspect
import time

from scripts.diagnostics.profile_cross_encoder_warmup import build_retriever_and_real_pairs


BATCH_SIZES = [1, 2, 4, 8, 10, 16, 32]
REPEATS = 3


def average(values: list[float]) -> float:
    return sum(values) / len(values)


def main() -> None:
    retriever, pairs = build_retriever_and_real_pairs()
    print(f"predict signature: {inspect.signature(retriever.cross_encoder.predict)}")
    print(f"Using {len(pairs)} real candidate pairs")

    # Warm up once before comparing batch-size settings.
    retriever.cross_encoder.predict(pairs)

    try:
        for batch_size in BATCH_SIZES:
            timings = []
            for _ in range(REPEATS):
                start = time.perf_counter()
                retriever.cross_encoder.predict(pairs, batch_size=batch_size)
                timings.append(time.perf_counter() - start)
            print(
                f"batch_size={batch_size:<2} "
                f"avg={average(timings):.4f}s "
                f"runs={[round(value, 4) for value in timings]}"
            )
    finally:
        retriever.store.close()


if __name__ == "__main__":
    main()
