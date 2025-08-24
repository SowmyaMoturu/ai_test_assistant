import logging
from typing import Any, Dict, List, Tuple
from langchain_core.messages import HumanMessage, BaseMessage, SystemMessage, AIMessage
from llm_wrappers.base_custom_model_llm import BaseCustomModelLLM

logger = logging.getLogger(__name__)

OPENAI_API_BASE_URL = "https://api.openai.com/v1/"

class OpenAIChatModel(BaseCustomModelLLM):
    """
    Wrapper for OpenAI Chat Completions API (text + image inputs).
    Mirrors the interface of GeminiModel to ease swapping.
    """

    api_base_url: str = OPENAI_API_BASE_URL
    # e.g., "gpt-5" / "gpt-4.1" / "gpt-4o" etc. Set via model_name in your base class.

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_request(self, messages: List[BaseMessage], **kwargs) -> Tuple[str, dict]:
        """
        Build Chat Completions payload.
        For images: we send them as content parts with image_url using a base64 data URL.
        """
        url = self.api_base_url + "chat/completions"
        openai_messages = self._process_messages(messages)

        payload = {
            "model": self.model_name,
            "messages": openai_messages,
            # tune as you like; keep defaults close to your Gemini config
            "temperature": kwargs.get("temperature", 0.2),
            "top_p": kwargs.get("top_p", 0.95),
            # you can add tools/function-calling here if needed
        }
        return url, payload

    def _process_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """
        Convert LangChain messages to OpenAI chat format, preserving roles.
        If HumanMessage has images (base64 pngs), add them as data URLs in the content array.
        """
        msgs = self.get_messages(messages)
        out: List[Dict[str, Any]] = []
        pending_system: str | None = None

        for m in msgs:
            if isinstance(m, SystemMessage):
                # stash the latest system prompt to prepend to next user message (like you did for Gemini)
                pending_system = (m.content or "").strip()
            elif isinstance(m, HumanMessage):
                content_parts: List[Dict[str, Any]] = []

                # include system text inline (keeps parity with your Gemini pattern)
                text = m.content or ""
                if pending_system:
                    text = f"{pending_system}\n{text}" if text else pending_system
                if text:
                    content_parts.append({"type": "text", "text": text})

                # images: expect base64 PNGs in additional_kwargs["images"]
                if hasattr(m, "additional_kwargs") and "images" in m.additional_kwargs:
                    for b64_png in m.additional_kwargs["images"]:
                        try:
                            data_url = f"data:image/png;base64,{self.clean_base64(b64_png)}"
                            content_parts.append({
                                "type": "image_url",
                                "image_url": {"url": data_url}
                            })
                        except Exception as e:
                            logger.error(f"Error processing image: {e}")

                out.append({"role": "user", "content": content_parts})
                pending_system = None

            elif isinstance(m, AIMessage):
                out.append({"role": "assistant", "content": m.content or ""})

            else:
                logger.warning(f"Unsupported message type: {type(m)}")

        return out

    def _parse_response(self, response_json: Dict[str, Any]) -> str:
        """
        Pull plain text back from Chat Completions.
        If you plan to support tool calls, extend this to handle choices[].message.tool_calls.
        """
        choices = response_json.get("choices", [])
        if not choices:
            logger.warning("No choices in OpenAI response")
            return ""

        # take the first choice's text content
        msg = choices[0].get("message", {})
        content = msg.get("content", "")
        if isinstance(content, list):
            # content could be parts; join text parts
            text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
            return "\n".join([t for t in text_parts if t])
        return content or ""
