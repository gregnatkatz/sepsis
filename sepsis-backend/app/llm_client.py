"""
LLM Client Wrapper for Azure OpenAI
Provides a unified interface for switching between different models (GPT-4.1, GPT-5, etc.)
"""

import os
import httpx
from typing import Dict, List, Any, Optional
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

class ModelType(str, Enum):
    """Available model types"""
    GPT41 = "gpt-4.1"
    GPT41_MINI = "gpt-4.1-mini"
    GPT41_NANO = "gpt-4.1-nano"
    GPT5 = "gpt-5"
    GPT5_CHAT = "gpt-5-chat"
    MODEL_ROUTER = "model-router"
    O1 = "o1"
    O3 = "o3"
    O4_MINI = "o4-mini"

class LLMClient:
    """Unified LLM client for Azure OpenAI models"""
    
    def __init__(self, model_type: Optional[ModelType] = None):
        """
        Initialize LLM client with specified model type.
        If no model_type is provided, uses DEFAULT_MODEL from environment.
        """
        self.model_type = model_type or ModelType(os.getenv("DEFAULT_MODEL", "gpt-4.1"))
        self.endpoint, self.api_key = self._get_model_config(self.model_type)
        
    def _get_model_config(self, model_type: ModelType) -> tuple[str, str]:
        """Get endpoint and API key for the specified model type"""
        config_map = {
            ModelType.GPT41: ("GPT41_ENDPOINT", "GPT41_API_KEY"),
            ModelType.GPT41_MINI: ("GPT41_MINI_ENDPOINT", "GPT41_MINI_API_KEY"),
            ModelType.GPT41_NANO: ("GPT41_NANO_ENDPOINT", "GPT41_NANO_API_KEY"),
            ModelType.GPT5: ("GPT5_ENDPOINT", "GPT5_API_KEY"),
            ModelType.GPT5_CHAT: ("GPT5_CHAT_ENDPOINT", "GPT5_CHAT_API_KEY"),
            ModelType.MODEL_ROUTER: ("MODEL_ROUTER_ENDPOINT", "MODEL_ROUTER_API_KEY"),
            ModelType.O1: ("O1_ENDPOINT", "O1_API_KEY"),
            ModelType.O3: ("O3_ENDPOINT", "O3_API_KEY"),
            ModelType.O4_MINI: ("O4_MINI_ENDPOINT", "O4_MINI_API_KEY"),
        }
        
        endpoint_key, api_key_key = config_map[model_type]
        endpoint = os.getenv(endpoint_key)
        api_key = os.getenv(api_key_key)
        
        if not endpoint or not api_key:
            raise ValueError(f"Missing configuration for {model_type}. Check .env file.")
        
        return endpoint, api_key
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict[str, str]] = None,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to the Azure OpenAI endpoint.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            response_format: Optional response format (e.g., {"type": "json_object"})
            timeout: Request timeout in seconds
            
        Returns:
            Response dictionary from Azure OpenAI
        """
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
        
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if response_format:
            payload["response_format"] = response_format
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self.endpoint,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def get_completion_text(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict[str, str]] = None,
        timeout: float = 60.0
    ) -> str:
        """
        Get the text content from a chat completion response.
        
        Args:
            Same as chat_completion()
            
        Returns:
            The text content of the assistant's response
        """
        response = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            timeout=timeout
        )
        
        return response["choices"][0]["message"]["content"]
    
    def switch_model(self, model_type: ModelType):
        """Switch to a different model type"""
        self.model_type = model_type
        self.endpoint, self.api_key = self._get_model_config(model_type)
    
    def get_current_model(self) -> ModelType:
        """Get the currently selected model type"""
        return self.model_type


def get_llm_client(model_type: Optional[ModelType] = None) -> LLMClient:
    """
    Create and return an LLM client instance.
    If no model_type is provided, uses DEFAULT_MODEL from environment.
    """
    return LLMClient(model_type=model_type)
