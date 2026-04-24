from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import Settings


SECURE_SYSTEM_PROMPT = (
    "You are a secure assistant. Use ONLY the provided context. "
    "If the answer is not in the context, say exactly: No information available for your role."
)


class SecureLLMClient:
    def generate_answer(self, question: str, context: str) -> str:
        raise NotImplementedError


@dataclass(slots=True)
class OpenAILLMClient(SecureLLMClient):
    api_key: str
    model: str
    _client: object = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=self.api_key)

    def generate_answer(self, question: str, context: str) -> str:
        completion = self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            max_tokens=512,
            messages=[
                {"role": "system", "content": SECURE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Question:\n{question}\n\nContext:\n{context}"},
            ],
        )
        message = completion.choices[0].message.content or ""
        return message.strip()


@dataclass(slots=True)
class HuggingFaceLLMClient(SecureLLMClient):
    api_token: str
    model: str
    _client: object = field(init=False, repr=False, default=None)
    _tokenizer: object = field(init=False, repr=False, default=None)

    def _get_client_and_tokenizer(self) -> tuple:
        if self._client is None:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._tokenizer = AutoTokenizer.from_pretrained(self.model)
            self._client = AutoModelForCausalLM.from_pretrained(self.model).to(device)
            self._device = device
        return self._client, self._tokenizer

    def generate_answer(self, question: str, context: str) -> str:
        model, tokenizer = self._get_client_and_tokenizer()
        prompt = f"{SECURE_SYSTEM_PROMPT}\n\nQuestion:\n{question}\n\nContext:\n{context}\n\nAnswer:"
        
        inputs = tokenizer(prompt, return_tensors="pt").to(self._device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
        )
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Extract only the new tokens (remove the prompt)
        answer = response[len(prompt):].strip()
        return answer


@dataclass(slots=True)
class GeminiLLMClient(SecureLLMClient):
    api_key: str
    model: str
    _client: object = field(init=False, repr=False, default=None)

    def _get_client(self) -> object:
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
        return self._client

    def generate_answer(self, question: str, context: str) -> str:
        client = self._get_client()
        prompt = f"{SECURE_SYSTEM_PROMPT}\n\nQuestion:\n{question}\n\nContext:\n{context}\n\nAnswer:"
        response = client.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 512,
            }
        )
        return response.text.strip()


def build_llm_client(settings: Settings) -> SecureLLMClient:
    provider = settings.llm_provider.strip().lower()
    if provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return OpenAILLMClient(api_key=settings.openai_api_key, model=settings.openai_model)

    if provider in {"huggingface", "hf"}:
        if not settings.huggingface_api_token:
            raise RuntimeError("HUGGINGFACE_API_TOKEN is required when LLM_PROVIDER=huggingface")
        return HuggingFaceLLMClient(api_token=settings.huggingface_api_token, model=settings.huggingface_model)

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        return GeminiLLMClient(api_key=settings.gemini_api_key, model=settings.gemini_model)

    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
