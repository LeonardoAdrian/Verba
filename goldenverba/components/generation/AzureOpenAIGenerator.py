import os
from goldenverba.data import database
from dotenv import load_dotenv
from goldenverba.components.interfaces import Generator
from goldenverba.components.types import InputConfig
from goldenverba.components.util import get_environment
import httpx
import json
import re
import base64
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
        print(full_response)                            
        
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
        if "imagen" in query.lower() or "img/" in context.lower():
            image_path = self.find_image_in_folder(query, context)
            if image_path:
                # Leer la imagen y convertirla a base64
                with open(image_path, "rb") as image_file:
                    encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
                
                # Agregar la imagen al contexto
                context += f"\n\n[Imagen encontrada: <img src='data:image/png;base64,{encoded_image}' alt='Imagen relacionada' />]"
                print(f'Contexto actualizado con imagen: {context}')
            else:
                context += "\n\nNo se encontró ninguna imagen que coincida con tu búsqueda."
                print(f'Contexto actualizado: {context}')
        database = config.get("DATABASE").value
        if database:
            async for result in self.metodo_previo(query, config, context, conversation):
                if result.get("finish_reason") == "stop" and result.get("message"):
                    context = f"\n\nSegun la base de datos esta es la respuesta con los datos mas recientes que responde el query del usuario:\n{str(result['message'])}"
                    print(f'Contexto actualizado: {context}')
                
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