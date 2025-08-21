from abc import abstractmethod
import time
import requests
from typing import Any, Dict, List, Optional, Tuple
from requests.exceptions import RequestException, HTTPError
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.messages import AIMessage
import logging
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class BaseCustomModelLLM(BaseChatModel, BaseModel):
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
        return "custom-chat-model-api"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        text = self._process_messages_with_retry(messages, stop=stop, **kwargs)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    def _process_messages_with_retry(self, messages: List[BaseMessage], **kwargs: Any) -> str:
        for attempt in range(self.max_retries):
            try:
                url, payload = self._build_request(messages, **kwargs)
                response = requests.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return self._parse_response(response.json())
            except HTTPError as e:
                if e.response is not None and e.response.status_code == 429 and attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limit exceeded. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"HTTPError on attempt {attempt + 1}: {e}")
                    raise
            except RequestException as e:
                logger.error(f"RequestException on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                else:
                    raise
            except Exception as e:
                logger.exception(f"Unexpected error on attempt {attempt + 1}: {e}")
                raise
        raise ConnectionError(f"Failed to get a response after {self.max_retries} attempts.")


    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def _build_request(self, messages: List[BaseMessage], **kwargs: Any) -> Tuple[str, dict]:
        pass

    @abstractmethod
    def _parse_response(self, response_json: dict) -> str:
        pass
    

    def get_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        if isinstance(messages, str):
            return [HumanMessage(content=messages)]
        elif isinstance(messages, list) and all(isinstance(m, str) for m in messages):
            return [HumanMessage(content=m) for m in messages]
        return messages

    @staticmethod
    def clean_base64(base64_string: str) -> str:
        return base64_string.strip().replace('\n',"")
    
