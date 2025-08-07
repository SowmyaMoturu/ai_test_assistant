import logging
from typing import Any, Dict, List, Tuple
from langchain_core.messages import HumanMessage, BaseMessage, SystemMessage, AIMessage
from llm_wrappers.base_custom_model_llm import BaseCustomModelLLM  
from llm_wrappers.config import GEMINI_API_BASE_URL

logger = logging.getLogger(__name__)

class GeminiModel(BaseCustomModelLLM):
    """
    Wrapper for Gemini API using Enterprise LangChain-compatible interface.
    Handles text + base64 image input and parses candidate responses.
    """

    api_base_url : str = GEMINI_API_BASE_URL

    def _get_headers(self) -> Dict[str, str]:
        """Provides the common headers for the API request."""
        # This can be overridden by child classes if they have different headers
        return {
            "X-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
    def _build_request(self, messages: List[BaseMessage], **kwargs) -> Tuple[str, dict]:
        url = self.api_base_url + self.model_name + ":generateContent"
        gemini_contents = self._process_messages(messages)
        return url, {
            "contents": gemini_contents,
            "model": self.model_name,
            "safety_settings": [
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_LOW_AND_ABOVE"
                }
            ],
            "generation_config": {
                "temperature": 0.2,
                "topP": 0.95,
                "topK": 40
            }
    }
    
    def _process_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        messages = self.get_messages(messages)
        gemini_contents = []
        system_prompt = None

        for message in messages:
            if isinstance(message, HumanMessage):
                gemini_contents.append(self._process_human_message(message, system_prompt))
                system_prompt = None  
            elif isinstance(message, SystemMessage):
                system_prompt = message.content.strip() if message.content else ""
            elif isinstance(message, AIMessage):
                gemini_contents.append({
                    "role": "assistant",
                    "parts": [{"text": message.content.strip()}]
                })
            else:
                logger.warning(f"Unsupported message type: {type(message)}")

        return gemini_contents

    def _process_human_message(self, message: HumanMessage, system_prompt: str = "") -> Dict[str, Any]:
        parts = []

        # Handle images if provided
        if hasattr(message, 'additional_kwargs') and 'images' in message.additional_kwargs:
            parts.extend(self._process_images(message.additional_kwargs['images']))

        # Handle message content
        if message.content:
            full_text = f"{system_prompt.strip()}\n{message.content.strip()}" if system_prompt else message.content
            parts.append({"text": full_text})

        return {
            "role": "user",
            "parts": parts
        }

    def _process_images(self, images: List[str]) -> List[Dict[str, Any]]:
        """
        Processes base64-encoded PNG images into Gemini API format.
        """
        processed = []
        for image_base64 in images:
            try:
                processed.append({
                    "inlineData": {
                        "mimeType": "image/png",
                        "data": self.clean_base64(image_base64)
                    }
                })
            except Exception as e:
                logger.error(f"Error processing image: {e}")
        return processed

    def _parse_response(self, response_json: Dict[str, Any]) -> str:
        parts = []

        for candidate_response in response_json.get("candidates", []):
            if isinstance(candidate_response, dict) and "content" in candidate_response:
                content = candidate_response["content"]
                if isinstance(content, dict) and "parts" in content:
                    for part in content.get("parts", []):
                        if isinstance(part, dict) and "text" in part:
                            text = part["text"]
                            parts.append(text)
                        else:
                            logger.warning(f"Unexpected part structure in parts list: {part}")
                else:
                    logger.warning(f"Missing or invalid 'parts' in content: {content}")
            else:
                logger.warning(f"Missing or invalid 'content' in candidate_response: {candidate_response}")

        return "\n".join(parts)

 
