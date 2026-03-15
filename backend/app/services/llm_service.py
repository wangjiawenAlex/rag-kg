"""
LLM Client Service.

Supports DeepSeek, 通义千问 (Tongyi Qianwen), and OpenAI compatible APIs.
"""

import json
import requests
from typing import List, Optional, Dict
from dataclasses import dataclass
import asyncio


@dataclass
class LLMResponse:
    """LLM response."""
    text: str
    usage: Dict[str, int]
    model: str


class LLMClient:
    """LLM API client."""
    
    # API endpoints
    API_ENDPOINTS = {
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
        "tongyi": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "openai": "https://api.openai.com/v1/chat/completions",
    }
    
    # Model mappings
    DEFAULT_MODELS = {
        "deepseek": "deepseek-chat",
        "tongyi": "qwen-turbo",
        "openai": "gpt-3.5-turbo",
    }
    
    def __init__(
        self,
        provider: str = "deepseek",
        api_key: str = None,
        api_base: str = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        """
        Initialize LLM client.
        
        Args:
            provider: LLM provider (deepseek, tongyi, openai)
            api_key: API key for the provider
            api_base: Custom API base URL (optional)
            model: Model name (defaults to provider's default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Set model
        if model:
            self.model = model
        else:
            self.model = self.DEFAULT_MODELS.get(self.provider, "gpt-3.5-turbo")
        
        # Set API base URL
        if api_base:
            self.api_base = api_base.rstrip('/')
        else:
            self.api_base = self.API_ENDPOINTS.get(self.provider, self.API_ENDPOINTS["openai"])
    
    def _build_messages(self, query: str, context: str = None, system_prompt: str = None) -> List[Dict]:
        """Build message payload for API call."""
        messages = []
        
        # System prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({
                "role": "system", 
                "content": "You are a helpful AI assistant. Answer based on the provided context."
            })
        
        # Context
        if context:
            messages.append({
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}"
            })
        else:
            messages.append({
                "role": "user",
                "content": query
            })
        
        return messages
    
    def _call_deepseek(self, messages: List[Dict]) -> LLMResponse:
        """Call DeepSeek API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        response = requests.post(
            self.api_base,
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        data = response.json()
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {}),
            model=data.get("model", self.model)
        )
    
    def _call_tongyi(self, messages: List[Dict]) -> LLMResponse:
        """Call Tongyi Qianwen (通义千问) API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "disable"  # Synchronous call
        }
        
        # Convert messages format for Tongyi
        content = messages[-1]["content"]  # Use the last user message
        if len(messages) > 1:
            # Add system context at the beginning
            system_content = messages[0]["content"] if messages[0]["role"] == "system" else ""
            if system_content:
                content = f"{system_content}\n\n{content}"
        
        payload = {
            "model": self.model,
            "input": {
                "prompt": content
            },
            "parameters": {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "result_format": "message"
            }
        }
        
        response = requests.post(
            self.api_base,
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        data = response.json()
        return LLMResponse(
            text=data["output"]["choices"][0]["message"]["content"],
            usage=data.get("usage", {}),
            model=data.get("model", self.model)
        )
    
    def _call_openai(self, messages: List[Dict]) -> LLMResponse:
        """Call OpenAI-compatible API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        response = requests.post(
            self.api_base,
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        data = response.json()
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {}),
            model=data.get("model", self.model)
        )
    
    async def generate(
        self,
        query: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        Generate response from LLM.
        
        Args:
            query: User query
            context: Retrieved context to use
            system_prompt: Custom system prompt
        
        Returns:
            LLMResponse with generated text
        """
        if not self.api_key:
            raise ValueError("API key is required")
        
        messages = self._build_messages(query, context, system_prompt)
        
        # Call appropriate API based on provider
        if self.provider == "deepseek":
            return self._call_deepseek(messages)
        elif self.provider == "tongyi":
            return self._call_tongyi(messages)
        elif self.provider == "openai":
            return self._call_openai(messages)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def generate_sync(
        self,
        query: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        Synchronous version of generate.
        
        Args:
            query: User query
            context: Retrieved context to use
            system_prompt: Custom system prompt
        
        Returns:
            LLMResponse with generated text
        """
        if not self.api_key:
            raise ValueError("API key is required")
        
        messages = self._build_messages(query, context, system_prompt)
        
        # Call appropriate API based on provider
        if self.provider == "deepseek":
            return self._call_deepseek(messages)
        elif self.provider == "tongyi":
            return self._call_tongyi(messages)
        elif self.provider == "openai":
            return self._call_openai(messages)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")


def create_llm_client(settings) -> Optional[LLMClient]:
    """
    Create LLM client from settings.
    
    Args:
        settings: Application settings
    
    Returns:
        LLMClient instance or None if not configured
    """
    if not settings.llm_api_key:
        return None
    
    return LLMClient(
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        api_base=settings.llm_api_base,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens
    )
