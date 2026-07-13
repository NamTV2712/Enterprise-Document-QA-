"""
Script: rag_smoke_test.py — runs manually to perform end-to-end testing before FastAPI is available.
"""
import logging

from configs.settings import settings
from src.generation.generator import Generator
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.embedder import Embedder
from src.retrieval.retriever import Retriever
from src.retrieval.vector_store import VectorStore

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

def main() -> None:
    generator = Generator(provider="groq")  # Change to "gemini" if needed.
    embedder = Embedder()
    with VectorStore(
        mode=settings.qdrant_mode,
        path=settings.qdrant_local_path,
        url=settings.qdrant_cloud_url,
        api_key=settings.qdrant_cloud_api_key,
    ) as store:
        retriever = Retriever(embedder=embedder, store=store)
        pipeline = RAGPipeline(retriever=retriever, generator=generator)

        questions = [
            ("What was Apple's total revenue in fiscal year 2024?",
             {"ticker": "AAPL", "section": "financial_statements"}),
            ("What are the main risk factors for Microsoft?",
             {"ticker": "MSFT", "section": "risk_factors"}),
            ("What is Amazon's AWS revenue growth?",
             {"ticker": "AMZN", "section": "mdna"}),
            ("What is Tesla's revenue in 2024?", {}),
        ]

        for question, filters in questions:
            print(f"\n{'='*60}")
            print(f"Q: {question}")
            print(f"{'='*60}")
            response = pipeline.query(question, top_k=5, **filters)
            print(f"\nA ({response.model_used}):\n{response.answer}")
            print(f"\n--- Sources used ({len(response.retrieved_chunks)} chunks) ---")
            for chunk in response.retrieved_chunks[:3]:
                print(f"  [{chunk.score:.4f}] {chunk.citation}")

if __name__ == "__main__":
    main()
