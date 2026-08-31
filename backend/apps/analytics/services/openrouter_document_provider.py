import json

from openai import APIConnectionError, APIStatusError, OpenAI

from .document_provider import (
    DOCUMENT_EXTRACTION_PROMPT,
    DocumentProviderError,
    attach_provider_metadata,
    parse_provider_json,
    read_visual_upload,
    validate_provider_result,
)


class OpenRouterDocumentProvider:
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"

    def __init__(self, *, api_key, model):
        self.api_key = api_key or ""
        self.model = model or ""

    @property
    def available(self):
        return bool(self.api_key)

    def extract_visual(self, upload):
        if not self.available:
            raise DocumentProviderError("missing_api_key", provider=self.name, model=self.model)
        data = read_visual_upload(upload)
        if data["content_type"] == "application/pdf" or data["filename"].lower().endswith(".pdf"):
            attachment = {
                "type": "file",
                "file": {"filename": data["filename"], "file_data": data["data_url"]},
            }
        else:
            attachment = {"type": "image_url", "image_url": {"url": data["data_url"]}}
        try:
            response = OpenAI(api_key=self.api_key, base_url=self.base_url).chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": DOCUMENT_EXTRACTION_PROMPT},
                    attachment,
                ]}],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            result = validate_provider_result(parse_provider_json(raw))
            return attach_provider_metadata(result, provider=self.name, model=self.model, upload_data=data)
        except DocumentProviderError as exc:
            if not exc.provider:
                exc.provider = self.name
                exc.model = self.model
            raise
        except (ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError) as exc:
            raise DocumentProviderError("invalid_provider_response", detail=exc.__class__.__name__, provider=self.name, model=self.model) from exc
        except (APIConnectionError, TimeoutError) as exc:
            raise DocumentProviderError("provider_timeout", detail=exc.__class__.__name__, provider=self.name, model=self.model) from exc
        except APIStatusError as exc:
            raise DocumentProviderError("provider_error", detail=exc.__class__.__name__, provider=self.name, model=self.model) from exc
        except Exception as exc:
            raise DocumentProviderError("provider_error", detail=exc.__class__.__name__, provider=self.name, model=self.model) from exc
