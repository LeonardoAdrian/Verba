import os
from dotenv import load_dotenv
from goldenverba.components.interfaces import Generator
from goldenverba.components.types import InputConfig
from goldenverba.components.util import get_environment
import httpx
import json

load_dotenv()


class AzureOpenAIGenerator(Generator):
    """
    Azure OpenAI Generator.
    """

    def __init__(self):
        super().__init__()
        self.name = "AzureOpenAI"
        self.description = "Using Azure OpenAI LLM models to generate answers to queries"
        self.context_window = 10000

        models = ["gpt-4o", "gpt-3.5-turbo", "gpt-35-turbo-16k"]

        self.config["Model"] = InputConfig(
            type="dropdown",
            value=models[0],
            description="Select an Azure OpenAI Model",
            values=models,
        )

        #if os.getenv("AZURE_OPENAI_API_KEY") is None:
        self.config["API Key"] = InputConfig(
            type="password",
            value="<ADD YOUR AZURE API KEY HERE>_",
            description="You can set your Azure OpenAI API Key here or set it as environment variable `AZURE_OPENAI_API_KEY`",
            values=[],
        )
        #if os.getenv("AZURE_OPENAI_BASE_URL") is None:
        self.config["URL"] = InputConfig(
            type="text",
            value="https://YOUR_RESOURCE_NAME.openai.azure.com",
            description="You can change the Base URL here if needed",
            values=[],
        )

        self.config["VERSION"] = InputConfig(
            type="text",
            value="2024-08-01-preview",
            description="Set your model version if needed",
            values=[],
        )

    async def generate_stream(
        self,
        config: dict,
        query: str,
        context: str,
        conversation: list[dict] = [],
    ):
        system_message = config.get("System Message").value
        #print(system_message)
        
        model = config.get("Model", {"value": "gpt-35-turbo-16k"}).value
        #print(model)
        
        azure_key = get_environment(
            config, "API Key", "AZURE_OPENAI_API_KEY", "No Azure OpenAI API Key found"
        )
        #print(azure_key)
        
        azure_url = get_environment(
            config, "URL", "AZURE_OPENAI_BASE_URL", "https://YOUR_RESOURCE_NAME.openai.azure.com"
        )
        #print(azure_url)

        version = config.get("VERSION", {"value": "2024-08-01-preview"}).value
        
        messages = self.prepare_messages(query, context, conversation, system_message)
        #print(messages)
        
        headers = {
            "Content-Type": "application/json",
            "api-key": azure_key,
        }
        data = {
            "messages": messages,
            "model": model,
            "stream": True,
        }
        print(f"Requesting to {azure_url}/openai/deployments/{model}/chat/completions?api-version={version}")
        print(f"Prompt: {data}")
        
        async with httpx.AsyncClient() as client2:
            async with client2.stream(
                "POST",
                f"{azure_url}/openai/deployments/{model}/chat/completions?api-version={version}",
                json=data,
                headers=headers,
                timeout=None,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        if line.strip() == "data: [DONE]":
                            break
                        json_line = json.loads(line[6:])
                        #print(json_line)
                        if "choices" in json_line and len(json_line["choices"]) > 0:
                            choice = json_line["choices"][0]
                            if "delta" in choice and "content" in choice["delta"]:
                                yield {
                                    "message": choice["delta"]["content"],
                                    "finish_reason": choice.get("finish_reason"),
                                }
                            elif "finish_reason" in choice:
                                yield {
                                    "message": "",
                                    "finish_reason": choice["finish_reason"],
                                }
                    else: print(response)
                            

    def prepare_messages(
        self, query: str, context: str, conversation: list[dict], system_message: str
    ) -> list[dict]:
        messages = [
            {
                "role": "system",
                "content": system_message,
            }
        ]

        for message in conversation:
            messages.append({"role": message.type, "content": message.content})

        messages.append(
            {
                "role": "user",
                "content": f"Answer this query: '{query}' with this provided context: {context}",
            }
        )

        return messages