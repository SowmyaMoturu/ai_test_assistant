from abc import abstractmethod
import time
import requests
from typing import Any, Dict, List, Optional, Tuple
from requests.exceptions import RequestException, HTTPError
from langchain_community.llms import BaseLLM
from langchain_core.outputs import Generation, LLMResult
import logging
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class BaseCustomModelLLM(BaseLLM, BaseModel):
    """Base class for any custom LLM (Claude, Gemini, etc.) that calls a custom API.
    
    This class handles common logic like API configuration, request handling with
    retries, and response parsing. Child classes must implement the abstract methods
    for building the request and parsing the response specific to their API.
    """
    
    model_name: str
    api_key: str
    max_retries: int = 3
    timeout: int = 60 # Set a default timeout for API requests

    # Use pydantic to enforce these types and make the class configurable
    # You can also add other optional parameters like `temperature` or `max_tokens`
    # and pass them down to the payload.

    @property
    def _llm_type(self) -> str:
        """Returns the type of the LLM for logging and identification."""
        return "custom-model-api"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Returns a dictionary of identifying parameters for the LLM.
        This is crucial for caching, tracing, and debugging.
        """
        return {
            "model_name": self.model_name}

    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """The core method for generating text completions.
        
        This method processes a list of prompts and returns an LLMResult
        object containing the generated text for each prompt.
        """
        generations = []
        for prompt in prompts:
            try:
                # The _process_prompt method handles the API call and retry logic
                text = self._process_prompt(prompt, stop=stop, **kwargs)
                generations.append([Generation(text=text)])
            except Exception as e:
                # Handle and log any exceptions to prevent a single failure
                # from stopping the entire batch.
                logger.error(f"Error generating for prompt: {e}")
                generations.append([Generation(text=f"[ERROR: {str(e)}]")])
                
        return LLMResult(generations=generations)

    def _process_prompt(self, prompt: str, **kwargs: Any) -> str:
        """
        Handles the API call for a single prompt with retry logic.
        """
        for attempt in range(self.max_retries):
            try:
                url, payload = self._build_request(prompt, **kwargs)
             # Make the API call with a timeout to prevent hanging
                response = requests.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                
                # If successful, parse and return the response
                return self._parse_response(response.json())
                
            except HTTPError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    # Handle rate limiting with exponential backoff
                    wait_time = 30 ** attempt
                    logger.warning(f"Rate limit exceeded. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Re-raise other HTTP errors
                    logger.error(f"HTTPError on attempt {attempt + 1}: {e}")
                    raise
            except RequestException as e:
                # Catches connection errors, timeouts, etc.
                logger.error(f"RequestException on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1) # Small delay before next retry
                else:
                    raise
            except Exception as e:
                # Catch any other unexpected errors
                logger.exception(f"Unexpected error on attempt {attempt + 1}: {e}")
                raise
        
        # If all retries fail, raise an exception or return an error message
        raise ConnectionError(f"Failed to get a response after {self.max_retries} attempts.")

    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        """Provides the common headers for the API request."""
        pass

    @abstractmethod
    def _build_request(self, prompt: str, **kwargs: Any) -> Tuple[str, dict]:
        """
        Abstract method to build the API request URL and payload.
        
        Args:
            prompt (str): The text prompt.
            **kwargs: Additional keyword arguments.
            
        Returns:
            A tuple containing the request URL and the JSON payload.
        """
        raise NotImplementedError

    @abstractmethod
    def _parse_response(self, response_json: dict) -> str:
        """
        Abstract method to parse the JSON response from the API.
        
        Args:
            response_json (dict): The JSON response from the API.
            
        Returns:
            The generated text as a string.
        """
        raise NotImplementedError
    
    def get_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:

        if isinstance(messages, str):
            return [HumanMessage(content=messages)]
        
        elif isinstance(messages, list) and all(isinstance(m, str) for m in messages):
            return [HumanMessage(content=m) for m in messages]
        
        return messages

    @staticmethod
    def clean_base64(base64_string: str) -> str:
        return base64_string.strip().replace('\n',"")
    
