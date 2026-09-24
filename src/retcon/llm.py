"""Runtime compatibility for models used by the Common AI task decorator."""
from urllib.parse import urlsplit

from pydantic_ai.models.openai import OpenAIChatModel


def configure_chat_model(model):
    """Use the standard token limit field for custom Chat Completions servers."""
    if (isinstance(model, OpenAIChatModel) and model.system == "openai"
            and model.provider is not None
            and urlsplit(model.provider.base_url).hostname != "api.openai.com"):
        # Changing OpenAIProvider.base_url keeps OpenAI's native profile. Local
        # servers such as LM Studio implement max_tokens instead of the newer
        # max_completion_tokens field. The hook caches this model for the task.
        model.profile["openai_chat_supports_max_completion_tokens"] = False
