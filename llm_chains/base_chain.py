from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel
from typing import Callable, List, Dict, Any
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser

class BaseChain(BaseModel):

    llm: Any
    output_parser: PydanticOutputParser
    prompt_func: Callable
    batch_size: int = 25
    max_items_per_request: int = 5

    def _prepare_llm_input(self, items: List[Dict[str, Any]]) -> List[HumanMessage]:
        # Default implementation, can be overridden
        prompt_text = self.prompt_func(items, self.output_parser.get_format_instructions())
        return [HumanMessage(content=prompt_text)]

    def process_single(self, item: Dict[str, Any]) -> Any:
        chain = self._prepare_llm_input| self.llm | self.output_parser
        return chain.invoke([item])
    
    def _process_single_token_batch(self, token_batch: List[Dict[str, Any]]) -> Any:
        chain = self._prepare_llm_input| self.llm | self.output_parser
        return  chain.invoke(token_batch)   


    def process_batch(self, batch: List[Dict[str, Any]]) -> List[Any]:
        with ThreadPoolExecutor(max_workers=min(len(batch), self.batch_size)) as executor:
            return list(executor.map(self.process_single, batch))
    
    def process_batched_items(self, items: List[Dict[str, Any]], max_chars: int = 200000) -> List[Any]:
        """
        Processes items in batches, each batch respecting token/character limits and max items per request.
        Each batch is sent as a single LLM request and results are aggregated.
        """
        batches = self._create_batched_items(items, max_chars=max_chars)
        results = []
        with ThreadPoolExecutor(max_workers=min(len(batches), self.batch_size)) as executor:
            batch_results = list(executor.map(self._process_single_token_batch, batches))
        for batch_result in batch_results:
            if isinstance(batch_result, list):
                results.extend(batch_result)
            else:
                results.append(batch_result)
        return results
    
    def _create_batched_items(self, items: List[Dict[str, Any]], max_chars: int = 200000) -> List[List[Dict[str, Any]]]:
        """
        Groups items into batches, respecting both character count (token limit)
        and the maximum number of items per request.
        """
        batches = []
        current_batch = []
        current_char_count = 0
    
        for item in items:
            item_text = str(item)
            item_chars = len(item_text)
    
            # Start a new batch if adding this item would exceed limits
            if (current_batch and
                (current_char_count + item_chars > max_chars or
                 len(current_batch) >= self.max_items_per_request)):
                batches.append(current_batch)
                current_batch = [item]
                current_char_count = item_chars
            else:
                current_batch.append(item)
                current_char_count += item_chars
    
        if current_batch:
            batches.append(current_batch)
    
        return batches
  