"""Test Ollama local model script.

Usage:
    python scripts/test_ollama.py

Prerequisites:
    - Ollama server running (default: http://localhost:11434)
    - Model pulled (default: llama3.2)
      Run: ollama pull llama3.2
"""

import asyncio
import sys
import time
from pathlib import Path

__test__ = False

sys.path.insert(0, str(Path(__file__).parent.parent))


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")


def print_ok(text: str) -> None:
    print(f"  [OK] {text}")


def print_skip(text: str) -> None:
    print(f"  [SKIP] {text}")


def print_fail(text: str) -> None:
    print(f"  [FAIL] {text}")


async def test_list_models(llm) -> bool:
    """Test 1: List available models from Ollama."""
    print_header("Test 1: List Available Models")
    try:
        models = await llm.list_models()
        if not models:
            print_skip("No models found on Ollama server")
            return False
        print_ok(f"Connected to Ollama server")
        print(f"  Available models ({len(models)}):")
        for m in models:
            print(f"    - {m}")
        return True
    except Exception as e:
        print_fail(f"Failed to connect: {e}")
        print("  Make sure Ollama is running: ollama serve")
        return False


async def test_non_streaming(llm) -> bool:
    """Test 2: Non-streaming generation."""
    print_header("Test 2: Non-Streaming Generation")
    try:
        prompt = "What is RAG? Answer in exactly one sentence."
        print(f"  Prompt: {prompt}")
        start = time.perf_counter()
        response = await llm.generate(prompt)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  Response ({elapsed:.0f}ms): {response}")
        print_ok(f"Non-streaming generation works ({elapsed:.0f}ms)")
        return True
    except Exception as e:
        print_fail(f"Failed: {e}")
        return False


async def test_streaming(llm) -> bool:
    """Test 3: Streaming generation."""
    print_header("Test 3: Streaming Generation")
    try:
        prompt = "List 3 benefits of RAG systems."
        print(f"  Prompt: {prompt}")
        start = time.perf_counter()
        full_response = ""
        token_count = 0
        print("  Response: ", end="", flush=True)
        async for token in llm.stream_generate(prompt):
            print(token, end="", flush=True)
            full_response += token
            token_count += 1
        elapsed = (time.perf_counter() - start) * 1000
        print()
        print_ok(f"Streaming generation works ({token_count} tokens, {elapsed:.0f}ms)")
        return True
    except Exception as e:
        print_fail(f"Failed: {e}")
        return False


async def test_conversation_history(llm) -> bool:
    """Test 4: Conversation with message history."""
    print_header("Test 4: Conversation with History")
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant that answers concisely."},
            {"role": "user", "content": "My name is Alice."},
            {"role": "assistant", "content": "Hello Alice! How can I help you today?"},
            {"role": "user", "content": "What is my name?"},
        ]
        print(f"  Message history: {len(messages)} messages")
        response = await llm.generate("What is my name?", messages=messages)
        print(f"  Response: {response}")

        if "alice" in response.lower():
            print_ok("Conversation history works correctly")
            return True
        else:
            print_fail("Model did not recall conversation history")
            return False
    except Exception as e:
        print_fail(f"Failed: {e}")
        return False


async def test_temperature_variation(llm) -> bool:
    """Test 5: Temperature variation."""
    print_header("Test 5: Temperature Variation")
    try:
        prompt = "Complete this sentence: The sky is"
        print(f"  Prompt: {prompt}")

        temps = [0.0, 0.7, 1.2]
        for temp in temps:
            response = await llm.generate(prompt, temperature=temp)
            label = "Deterministic" if temp < 0.3 else "Balanced" if temp < 1.0 else "Creative"
            print(f"  temp={temp:.1f} ({label}): {response[:80]}{'...' if len(response) > 80 else ''}")

        print_ok("Temperature variation works")
        return True
    except Exception as e:
        print_fail(f"Failed: {e}")
        return False


async def test_long_context(llm) -> bool:
    """Test 6: Long context with num_ctx."""
    print_header("Test 6: Context Window (num_ctx)")
    try:
        long_text = (
            "Here is a list of facts: "
            "1. The capital of France is Paris. "
            "2. The largest planet in the solar system is Jupiter. "
            "3. Python was created by Guido van Rossum. "
            "4. The speed of light is approximately 299,792 km/s. "
        ) * 20  # repeat to make it longer
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"{long_text}\n\nBased on the text above, what is the capital of France?"},
        ]
        print(f"  Sending {len(long_text)} chars as context...")

        # Test with larger context window
        response = await llm.generate(
            "What is the capital of France?",
            messages=messages,
            num_ctx=8192,
        )
        print(f"  Response: {response}")

        if "paris" in response.lower():
            print_ok("Long context handling works")
            return True
        else:
            print_fail("Model did not recall context correctly")
            return False
    except Exception as e:
        print_fail(f"Failed: {e}")
        return False


async def test_token_estimation(llm) -> bool:
    """Test 7: Token estimation."""
    print_header("Test 7: Token Estimation")
    try:
        test_texts = [
            "Hello world",
            "The quick brown fox jumps over the lazy dog.",
            "RAG (Retrieval-Augmented Generation) combines retrieval and generation for better AI responses.",
        ]
        for text in test_texts:
            count = await llm.count_tokens(text)
            print(f"  Text ({len(text)} chars): ~{count} tokens")

        print_ok("Token estimation works")
        return True
    except Exception as e:
        print_fail(f"Failed: {e}")
        return False


async def test_llm_service_integration() -> bool:
    """Test 8: LLMService with Ollama provider."""
    print_header("Test 8: LLMService Integration")
    try:
        from app.services.llm_service import LLMService

        service = LLMService(
            provider="ollama",
            model="llama3.2",
            timeout=120,
        )

        print("  Testing generate()...")
        response = await service.generate("What is 2+2?")
        print(f"  Response: {response}")

        print("  Testing stream_generate()...")
        print("  Stream: ", end="", flush=True)
        async for token in service.stream_generate("What is 3+3?"):
            print(token, end="", flush=True)
        print()

        print_ok("LLMService with ollama provider works")
        return True
    except Exception as e:
        print_fail(f"Failed: {e}")
        return False


async def test_performance(llm) -> bool:
    """Test 9: Performance benchmark."""
    print_header("Test 9: Performance Benchmark")
    try:
        prompts = [
            "What is artificial intelligence?",
            "Explain machine learning in one sentence.",
            "What are the benefits of using RAG?",
        ]

        total_time = 0
        total_tokens = 0

        for i, prompt in enumerate(prompts, 1):
            start = time.perf_counter()
            response = await llm.generate(prompt)
            elapsed = (time.perf_counter() - start) * 1000
            tokens = await llm.count_tokens(response)
            total_time += elapsed
            total_tokens += tokens
            print(f"  Prompt {i}: {elapsed:.0f}ms, ~{tokens} tokens")

        avg_time = total_time / len(prompts)
        avg_tokens = total_tokens / len(prompts)
        print(f"  Average: {avg_time:.0f}ms/prompt, ~{avg_tokens:.0f} tokens/prompt")
        print_ok("Performance benchmark completed")
        return True
    except Exception as e:
        print_fail(f"Failed: {e}")
        return False


async def main():
    """Run all Ollama tests."""
    from app.capabilities.llm import OllamaLLM
    from app.config import get_settings

    settings = get_settings()

    print()
    print("=" * 60)
    print("  SmartRAG — Ollama Local Model Test Suite")
    print("=" * 60)
    print(f"  Ollama URL:  {settings.OLLAMA_BASE_URL}")
    print(f"  Model:      {settings.OLLAMA_MODEL}")
    print(f"  Context:    {settings.OLLAMA_NUM_CTX} tokens")
    print(f"  Temperature: {settings.OLLAMA_TEMPERATURE}")
    print(f"  Timeout:    {settings.OLLAMA_TIMEOUT}s")

    llm = OllamaLLM()

    # Run all tests
    results = {
        "List Models": await test_list_models(llm),
        "Non-Streaming": await test_non_streaming(llm),
        "Streaming": await test_streaming(llm),
        "Conversation History": await test_conversation_history(llm),
        "Temperature Variation": await test_temperature_variation(llm),
        "Long Context": await test_long_context(llm),
        "Token Estimation": await test_token_estimation(llm),
        "LLMService Integration": await test_llm_service_integration(),
        "Performance Benchmark": await test_performance(llm),
    }

    # Summary
    print_header("Test Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")

    print()
    print(f"  Result: {passed}/{total} tests passed")
    print()
    if passed == total:
        print("  All tests passed! Ollama is fully integrated.")
    else:
        print("  Some tests failed. Check the output above for details.")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
