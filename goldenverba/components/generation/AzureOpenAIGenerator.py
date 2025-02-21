import os
from goldenverba.data import database
from dotenv import load_dotenv
from goldenverba.components.interfaces import Generator
from goldenverba.components.types import InputConfig
from goldenverba.components.util import get_environment, get_token
import httpx
import json
from typing import List
import requests
import re
from psycopg2 import sql as psql


load_dotenv()


class AzureOpenAIGenerator(Generator):
    """
    Azure OpenAI Generator.
    """

    def __init__(self):
        super().__init__()
        self.db = database.DatabaseConnection()
        self.name = "AzureOpenAI"
        self.description = "Using Azure OpenAI LLM models to generate answers to queries"
        self.context_window = 10000

        

        api_key = get_token("AZURE_OPENAI_API_KEY")
        resource_name = get_token("AZURE_RESOURCE_NAME")
        base_url = f"https://{resource_name}.openai.azure.com"
        models = self.get_models(api_key, base_url)

        self.config["Model"] = InputConfig(
            type="dropdown",
            value=models[0],
            description="Select an Azure OpenAI Inference Model",
            values=models,
        )

        if api_key is None:
            self.config["API Key"] = InputConfig(
                type="password",
                value="<ADD YOUR AZURE API KEY HERE>",
                description="You can set your Azure OpenAI API Key here or set it as environment variable `AZURE_OPENAI_API_KEY`",
                values=[],
            )
        if resource_name is None:
            self.config["RESOURCE NAME"] = InputConfig(
                type="text",
                value="",
                description="You can set your Azure Resource Name here or set it as evironment variable `AZURE_RESOURCE_NAME`",
                values=[],
            )

        self.config["VERSION"] = InputConfig(
            type="text",
            value="2024-08-01-preview",
            description="Set your model version if needed",
            values=[],
        )
        
        self.config["DATABASE"] = InputConfig(
            type="bool",
            value=0,
            description="Marque la casilla si va a realizar preguntas sobre información que se encuentra en una base de datos.",
            values=[],
        )
    

    def extract_sql_query(self,full_text: str) -> str:
       
        match = re.search(r"SELECT.*?;", full_text, re.DOTALL)
        if match:
            sql_query = match.group(0).strip().replace("\n", " ")
            return sql_query
        return ""

    async def metodo_previo(
        self,
        query: str,
        config: dict,
        context: str,
        conversation: list[dict] = [],
    ):
        system_message = config.get("System Message").value
        model = config.get("Model", {"value": "gpt-35-turbo-16k"}).value
        azure_key = get_environment(
            config, "API Key", "AZURE_OPENAI_API_KEY", "No Azure OpenAI API Key found"
        )
        azure_url = get_environment(
            config, "URL", "AZURE_OPENAI_BASE_URL", "https://YOUR_RESOURCE_NAME.openai.azure.com"
        )
        version = config.get("VERSION", {"value": "2024-08-01-preview"}).value

        # Preparar el mensaje para la API
        messages = self.prepare_messages_query(
            query + ', de la pregunta que te hice, solo dame el query SQL usando el esquema de la base de datos que te proporcioné. No incluyas explicaciones ni texto adicional, solo el query SQL.',
            context,
            conversation,
            system_message
        )
        print(f'Mensaje enviado a la API: {messages}')

        headers = {
            "Content-Type": "application/json",
            "api-key": azure_key,
        }
        data = {
            "messages": messages,
            "model": model,
            "stream": True,
        }

        full_response = ""

        async with httpx.AsyncClient() as client:
            async with client.stream(
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
                        if "choices" in json_line and len(json_line["choices"]) > 0:
                            choice = json_line["choices"][0]
                            if "delta" in choice and "content" in choice["delta"]:
                                full_response += choice["delta"]["content"]
                            elif "finish_reason" in choice:
                                pass                           
        
        sql_query = self.extract_sql_query(full_response)
        if sql_query:
            print(f"Query SQL extraído: {sql_query}")
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(psql.SQL(sql_query))
                    results = cur.fetchall()  
            
            yield {
                "message": results, 
                "finish_reason": "stop",
            }
        else:
            print("No se encontró un query SQL en la respuesta.")
            yield {
                "message": full_response.strip(),  
                "finish_reason": "stop",
            }
                    
        

   
    async def generate_stream(
        self,
        config: dict,
        query: str,
        context: str,
        conversation: list[dict] = [],
    ):
        system_message = config.get("System Message").value
        model = config.get("Model", {"value": "gpt-35-turbo-16k"}).value
        azure_key = get_environment(
            config, "API Key", "AZURE_OPENAI_API_KEY", "No Azure OpenAI API Key found"
        )
        
        resource_name = get_environment(
            config, "RESOURCE NAME", "AZURE_RESOURCE_NAME", "No Resource Name found"
        )
        if resource_name is None:
            resource_name = config.get("RESOURCE NAME").value
            
        azure_url = f"https://{resource_name}.openai.azure.com"
        version = config.get("VERSION", {"value": "2024-08-01-preview"}).value
                
        messages = self.prepare_messages(query, context, conversation, system_message)
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
    
    def find_image_in_folder(self, query: str, context: str) -> str:
        # Buscar en la carpeta img/ archivos que coincidan con el query o el contexto
        img_folder = "img/"
        if not os.path.exists(img_folder):
            return ""

        # Buscar archivos en la carpeta img/
        for filename in os.listdir(img_folder):
            if filename.lower() in query.lower() or  filename.lower() in context.lower():
                return os.path.join(img_folder, filename)

        return ""                       
    def prepare_messages_query(
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
    
    @staticmethod
    def get_models(token: str, url: str) -> List[str]:
        api_version = "2024-10-21"
        url = f"{url}/openai/models?api-version={api_version}"
        headers = {"api-key": token} if token else {}
        
        default_models = ["gpt-4o", "gpt-3.5-turbo", "gpt-35-turbo-16k"]
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [model["id"] for model in data.get("data", []) if model["capabilities"].get("inference")]
        except (requests.RequestException, KeyError):
            return default_models