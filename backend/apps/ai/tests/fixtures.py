"""Synthetic-only fixtures for AI-INTELLIGENCE-01 tests."""
import json
from unittest.mock import Mock


def openrouter_message(content=None, tool_calls=None, finish_reason="stop"):
    message = Mock()
    message.content = content
    message.tool_calls = tool_calls or []
    return message


def tool_call(id, name, arguments):
    call = Mock()
    call.id = id
    call.function = Mock()
    call.function.name = name
    call.function.arguments = json.dumps(arguments)
    return call


def openrouter_response(*, content=None, tool_calls=None, finish_reason="stop", model="test/model",
                        prompt_tokens=10, completion_tokens=5):
    response = Mock()
    response.model = model
    choice = Mock()
    choice.message = openrouter_message(content=content, tool_calls=tool_calls, finish_reason=finish_reason)
    choice.finish_reason = finish_reason
    response.choices = [choice]
    response.usage = Mock(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return response
