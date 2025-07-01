# llm_client.py
import ollama
from ollama import ChatResponse
import json # For pretty printing response if needed
from typing import Union, Iterable, Generator

class LLMClient:
    """
    A simple interface to interact with a local Ollama LLM.
    """
    def __init__(self, 
                 model_name: str = "gemma3:12b",
                 host: str = "http://localhost:11434",
                 max_response_length: int = 2500,
                 system_prompt_allowed: bool = False,
                 images_allowed: bool = False,
                 context_length: int = 8192,
                 temperature: float = 0.7):
        """
        Initializes the OllamaLLM interface.

        Args:
            model_name (str): The name of the Ollama model to use (e.g., "gemma3:12b", "llama3").
            host (str): The URL of the Ollama server.
            max_response_length (int): Maximum number of tokens/words the LLM should generate in its response.
                                       Corresponds to Ollama's 'num_predict' option.
            system_prompt_allowed (bool): If False, messages with role "system" will be filtered out.
            images_allowed (bool): If False, messages containing an "images" key will be filtered out.
            context_length (int): The context window size (number of tokens) for the model.
                                Corresponds to Ollama's 'num_ctx' option.
        """
        self.model_name = model_name
        self.host = host
        self.max_response_length = max_response_length
        self.system_prompt_allowed = system_prompt_allowed
        self.images_allowed = images_allowed
        self.context_length = context_length
        self.temperature = temperature

    def generate_response(self, chat_messages: list, temperature: float = 0.7, stream_response: bool = False) -> Union[ChatResponse, Iterable[ChatResponse]]:
        """
        Generates a text response from the Ollama model.

        Args:
            prompt (str): The user's input prompt.
            chat_messages (list): A list of message dictionaries for context.
                                 Each message is {"role": "user"|"assistant"|"system", "content": "text", "images": [...]}.
            temperature (float): Controls the randomness of the response. Higher means more random.
            stream (bool): If True, returns a generator that yields response text chunks as they're generated.
                          If False, returns the complete response as a ChatResponse object.

        Returns:
            Union[ollama.ChatResponse, Iterable[str]]: 
                The generated response from the LLM. If stream=True, returns an iterable of 
                text strings. If stream=False, returns a ChatResponse object.
        """

        # Prepare Ollama options
        ollama_options = {
            "temperature": self.temperature,
            "num_predict": self.max_response_length,
            "num_ctx": self.context_length,
        }

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=chat_messages,
                options=ollama_options,
                stream=stream_response
            )
            
            return response
            
        except ollama.ResponseError as e:
            error_msg = None
            if "connection refused" in str(e).lower() or "connectex" in str(e).lower():
                error_msg = f"Error: Could not connect to Ollama server at {self.host}. Is Ollama running?"
            elif "model not found" in str(e).lower():
                error_msg = f"Error: Model '{self.model_name}' not found. Please run 'ollama pull {self.model_name}'."
            else:
                error_msg = f"Error generating response: {e}"
            
            # For errors, we'll need to handle this differently since we're returning specific types
            # You may want to raise the exception or handle errors according to your application's needs
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"An unexpected error occurred: {e}"
            raise Exception(error_msg)


    def list_installed_models(self) -> list:
        """
        Retrieves a list of names of models currently installed in Ollama.

        Returns:
            list: A list of model names (strings), or an error message string if connection fails.
        """
        try:
            response = ollama.list()
            model_names = [model for model in response.get('models', [])]
            return model_names
        except ollama.ResponseError as e:
            if "connection refused" in str(e).lower() or "connectex" in str(e).lower():
                return [f"Error: Could not connect to Ollama server at {self.host}. Is Ollama running?"]
            else:
                return [f"Error listing models: {e}"]
        except Exception as e:
            return [f"An unexpected error occurred: {e}"]

def get_model_info(model_name) -> ollama.ShowResponse:
    """
    Retrieves information about the configured Ollama model.
    """
    return ollama.show(model_name)