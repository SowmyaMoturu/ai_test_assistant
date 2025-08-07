import logging
from typing import Any, Dict, List, Tuple

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

from llm_wrappers.base_custom_model_llm import BaseCustomModelLLM
from llm_wrappers.config import CLAUDE_API_BASE_URL

logger = logging.getLogger(__name__)

class ClaudeModel(BaseCustomModelLLM):
    """
    Wrapper for Anthropic Claude API using Enterprise LangChain-compatible interface.
    Handles multi-turn conversation with system + user + assistant messages.
    """

    api_base_url : str = CLAUDE_API_BASE_URL
   
    def _get_headers(self) -> Dict[str, str]:
        """Provides the common headers for the API request."""
        # This can be overridden by child classes if they have different headers
        return {
            "anthropic-version": "2023-06-01",
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _build_request(self, messages: List[BaseMessage], **kwargs) -> Tuple[str, dict]:
        url = self.api_base_url
        claude_messages = self._process_messages(messages)

        return url, {
            "messages": claude_messages,
            "model": self.model_name,
            "max_tokens": 4096
        }

    def _process_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        claude_messages = []
        system_prompt = None
        for message in self.get_messages(messages):
            if isinstance(message, SystemMessage):
                system_prompt = message.content.strip()
                claude_messages.append({"role": "system", "content": system_prompt})
            elif isinstance(message, HumanMessage):
                text = message.content.strip()
                if system_prompt:
                    text = f"{system_prompt}\n{text}"
                    system_prompt = None
                claude_messages.append({"role": "user", "content": text})
            elif isinstance(message, AIMessage):
                claude_messages.append({"role": "assistant", "content": message.content.strip()})
            else:
                logger.warning(f"Unsupported message type: {type(message)}")
        return claude_messages
    
    def _process_human_message(self, message: HumanMessage, system_prompt: str = "") -> Dict[str, Any]:
        content = [{"type": "text", "text": message.content.strip()}]
        if hasattr(message, 'additional_kwargs') and 'images' in message.additional_kwargs:
            content.extend(self._process_images(message.additional_kwargs['images']))
                    
        return {
            "role": "user",
            "content": content
        }
    
    def _process_images(self, images: List[str]) -> List[Dict[str, Any]]:
        return [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "data": self.clean_base64(image),
                    "media_type": "image/png"
                }
            }
            for image in images if image.strip()
        ]


    def _parse_response(self, response_json: Dict[str, Any]) -> str:
        """
        Parse Claude's response JSON and extract the content from the assistant.
        """
        try:
            return response_json["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to parse Claude response: {e}")
            return ""
