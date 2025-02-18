import os
import json
from typing import List
import io
import requests
import aiohttp
from wasabi import msg
import asyncio

from goldenverba.components.interfaces import Embedding
from goldenverba.components.types import InputConfig
from goldenverba.components.util import get_environment, get_token


class AzureOpenAIEmbedder(Embedding):
    """OpenAIEmbedder for Verba."""

    def __init__(self):
        super().__init__()
        self.name = "AzureOpenAI"
        self.description = "Vectorizes documents and queries using Azure OpenAI"

        # Fetch available models
        api_key = get_token("AZURE_OPENAI_API_KEY")
        resource_name = get_token("AZURE_RESOURCE_NAME")
        base_url = f"https://{resource_name}.openai.azure.com"
        models = self.get_models(api_key, base_url)

        # Set up configuration
        self.config = {
            "Model": InputConfig(
                type="dropdown",
                value=models[0],
                description="Select an OpenAI Embedding Model",
                values=models,
            )
        }

        # Add API Key and URL configs if not set in environment
        if api_key is None:
            self.config["API Key"] = InputConfig(
                type="password",
                value="",
                description="Azure OpenAI Key (or set AZURE_OPENAI_API_KEY env var)",
                values=[],
            )

        if resource_name is None:
            self.config["RESOURCE NAME"] = InputConfig(
                type="text",
                value="",
                description="Azure OpenAI Resource Name",
                values=[],
            )

        self.config["VERSION"] = InputConfig(
            type="text",
            value="2023-05-15",
            description="Set your embedding model version if needed",
            values=[],
        )

    async def vectorize(self, config: dict, content: List[str]) -> List[List[float]]:
        """Vectorize the input content using OpenAI's API."""
        model = config.get("Model", {"value": "text-embedding-ada-002"}).value

        api_key = get_environment(
            config, "API Key", "AZURE_OPENAI_API_KEY", "No OpenAI API Key found"
        )

        resource_name = get_environment(
            config, "RESOURCE NAME", "AZURE_RESOURCE_NAME", "No Resource Name found"
        )
        if resource_name is None:
            resource_name = config.get("RESOURCE NAME").value

        base_url = f"https://{resource_name}.openai.azure.com"
        version = config.get("VERSION", {"value": "2023-05-15"}).value

        headers = {
            "Content-Type": "application/json",
            "api-key": api_key,
        }
        payload = {"input": content}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{base_url}/openai/deployments/{model}/embeddings?api-version={version}",
                    headers=headers,
                    json=payload,
                    timeout=30,
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    if "data" not in data:
                        raise ValueError(f"Unexpected API response: {data}")

                    embeddings = [item["embedding"] for item in data["data"]]
                    if len(embeddings) != len(content):
                        raise ValueError(
                            f"Mismatch in embedding count: got {len(embeddings)}, expected {len(content)}"
                        )
                    return embeddings
            except aiohttp.ClientError as e:
                if isinstance(e, aiohttp.ClientResponseError) and e.status == 429:
                    raise Exception("Rate limit exceeded. Waiting before retrying...")
                raise Exception(f"API request failed: {str(e)}")

            except Exception as e:
                msg.fail(f"Unexpected error: {type(e).__name__} - {str(e)}")
                raise
        

    @staticmethod
    def get_models(token: str, url: str) -> List[str]:
        api_version = "2024-10-21"
        url = f"{url}/openai/models?api-version={api_version}"
        headers = {"api-key": token} if token else {}
        
        default_models = [
            "text-embedding-ada-002",
            "text-embedding-3-small",
            "text-embedding-3-large",
        ]
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [model["id"] for model in data.get("data", []) if model["capabilities"].get("embeddings")]
        except (requests.RequestException, KeyError):
            return default_models
