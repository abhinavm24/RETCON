"""Exercise the actual model and SDK serialization without making network calls."""
import json

import httpx2
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider
import pytest

from retcon.llm import configure_chat_model


def completion_handler(requests):
    def respond(request):
        requests.append(json.loads(request.content))
        return httpx2.Response(200, json={
            "id": "offline-completion", "object": "chat.completion", "created": 0, "provider": "Fixture",
            "model": requests[-1]["model"],
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant", "content": "The repaired paragraph.",
            }}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })
    return respond


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint,token_field", [
    ("http://127.0.0.1:1234/v1", "max_tokens"),
    ("http://host.docker.internal:1234/v1", "max_tokens"),
    ("https://api.openai.com/v1", "max_completion_tokens"),
])
async def test_chat_token_budget_reaches_the_wire_for_compatible_and_native_endpoints(endpoint, token_field):
    requests = []
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(completion_handler(requests))) as client:
        provider = OpenAIProvider(base_url=endpoint, api_key="fixture-only-key", http_client=client)
        model = OpenAIChatModel("qwen3.8-27b-uncensored-mlx", provider=provider)
        configure_chat_model(model)
        result = await Agent(model).run("Repair this paragraph.", model_settings={"max_tokens": 1800})
    assert result.output == "The repaired paragraph."
    assert requests[0][token_field] == 1800
    other_field = "max_completion_tokens" if token_field == "max_tokens" else "max_tokens"
    assert other_field not in requests[0]


@pytest.mark.asyncio
async def test_openrouter_keeps_its_native_profile_and_payload():
    requests = []
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(completion_handler(requests))) as client:
        provider = OpenRouterProvider(api_key="fixture-only-key", http_client=client)
        model = OpenRouterModel("google/gemma-4-31b-it:free", provider=provider)
        original_profile = dict(model.profile)
        configure_chat_model(model)
        assert model.profile == original_profile
        result = await Agent(model).run("Repair this paragraph.", model_settings={"max_tokens": 1800})
    assert result.output == "The repaired paragraph."
    assert requests[0]["max_tokens"] == 1800
    assert "max_completion_tokens" not in requests[0]
