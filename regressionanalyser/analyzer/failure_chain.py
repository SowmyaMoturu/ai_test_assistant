from llm_chains.base_chain import BaseChain
from langchain_core.messages import HumanMessage
from typing import List, Dict, Any

class FailureChain(BaseChain):
    mode: str = "api"  # or "ui"

    def _prepare_llm_input(self, failures: List[Dict[str, Any]]) -> List[HumanMessage]:
        if self.mode == "ui":
            failure = failures[0]
            # Remove screenshot from prompt input
            failure_for_prompt = {k: v for k, v in failure.items() if k != "screenshot"}
            prompt_text = self.prompt_func(failure_for_prompt, self.output_parser.get_format_instructions())
            screenshot = failure.get("screenshot")
            if screenshot:
                return [HumanMessage(content=prompt_text, additional_kwargs={"images": [screenshot]})]
            return [HumanMessage(content=prompt_text)]
        else:
            # API mode: batch failures, no screenshots
            failures_for_prompt = [{k: v for k, v in f.items() if k != "screenshot"} for f in failures]
            prompt_text = self.prompt_func(failures_for_prompt, self.output_parser.get_format_instructions())
            return [HumanMessage(content=prompt_text)]

    def process_batched_items(self, items: List[Dict[str, Any]], max_chars: int = 200000) -> List[Any]:
        """
        Removes screenshots from each failure before batching and processing.
        """
        items_no_screenshot = [{k: v for k, v in item.items() if k != "screenshot"} for item in items]
        return super().process_batched_items(items_no_screenshot, max_chars=max_chars)

    def run(self, failures: List[Dict[str, Any]]) -> List[Any]:
        if self.mode == "ui":
            return self.process_batch(failures)
        else:
            return self.process_batched_items(failures)