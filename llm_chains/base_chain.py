from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
import time
from langchain_core.prompts import PromptTemplate

import logging

logger = logging.getLogger(__name__)

class BaseChain(BaseModel):

    llm: Any
    output_parser: PydanticOutputParser
    prompt_template: PromptTemplate
    batch_size: int = 25
    max_items_per_request: int = 5
    delay_between_batches: int = 60


    def _prepare_llm_input(self, items: List[Dict[str, Any]]) -> List[HumanMessage]:
        # Default implementation, can be overridden
        prompt_text = self.prompt_template.format(items, self.output_parser.get_format_instructions())
        return [HumanMessage(content=prompt_text)]

    def process_single(self, item: Dict[str, Any]) -> Any:
        chain = self._prepare_llm_input| self.llm | self.output_parser
        return chain.invoke([item])
    
    def _process_single_token_batch(self, token_batch: List[Dict[str, Any]]) -> List[Any]:
        chain = self._prepare_llm_input| self.llm | self.output_parser
        return chain.invoke(token_batch)

    def process_batch(self, batch: List[Dict[str, Any]]) -> List[Any]:
        num_items = len(batch)
        batch_size = self.batch_size
        num_batches = (num_items + batch_size - 1) // batch_size
        all_results = []
        start_time = time.time()

        for i in range(0, num_items, batch_size):
            batch_items = batch[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            logger.info(f"Processing batch {batch_num}/{num_batches} with {len(batch_items)} items.")

            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                batch_results = list(executor.map(self.process_single, batch_items))
            all_results.extend(batch_results)

            if batch_num < num_batches and self.delay_between_batches_s > 0:
                logger.info(f"Batch {batch_num} finished. Waiting for {self.delay_between_batches_s} seconds.")
                time.sleep(self.delay_between_batches_s)

        execution_time = time.time() - start_time
        logger.info(f"Batch processing completed in {execution_time:.2f} seconds.")
        return all_results
    
    def process_batched_items(self, items: List[Dict[str, Any]], max_chars: int = 200000) -> List[Any]:
        """
        Processes items in batches, each batch respecting token/character limits and max items per request.
        Each batch is sent as a single LLM request and results are aggregated.
        Processes batches in groups of self.batch_size, with delay between groups.
        """
        batches = self._create_batched_items(items, max_chars=max_chars)
        total_batches = len(batches)
        results = []
        start_time = time.time()
        num_groups = (total_batches + self.batch_size - 1) // self.batch_size

        for group_idx in range(0, total_batches, self.batch_size):
            group_batches = batches[group_idx:group_idx + self.batch_size]
            group_num = (group_idx // self.batch_size) + 1
            logger.info(f"Processing batch group {group_num}/{num_groups} with {len(group_batches)} sub-batches.")

            with ThreadPoolExecutor(max_workers=len(group_batches)) as executor:
                batch_results = list(executor.map(self._process_single_token_batch, group_batches))
            for batch_result in batch_results:
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                else:
                    results.append(batch_result)

            if group_num < num_groups and getattr(self, "delay_between_batches_s", 0) > 0:
                logger.info(f"Batch group {group_num} finished. Waiting for {self.delay_between_batches} seconds.")
                time.sleep(self.delay_between_batches)

        execution_time = time.time() - start_time
        logger.info(f"Batched item processing completed in {execution_time:.2f} seconds.")
        return results
    
    def _create_batched_items(self, items: List[Dict[str, Any]], max_chars: int = 200000) -> List[List[Dict[str, Any]]]:
        """
        Groups items into batches, respecting both character count (token limit)
        and the maximum number of items per request.
        """
        batches = []
        current_batch = []
        current_char_count = 0
        dropped_items = []

        for idx, item in enumerate(items):
            item_text = str(item)
            item_chars = len(item_text)

            # If item itself exceeds max_chars, drop and log it
            if item_chars > max_chars:
                logger.warning(f"Item at index {idx} exceeds max_chars ({max_chars}) and will be dropped.")
                dropped_items.append(item)
                continue

            # Start a new batch if adding this item would exceed limits
            if (current_batch and
                (current_char_count + item_chars > max_chars or
                 len(current_batch) >= self.max_items_per_request)):
                batches.append(current_batch)
                current_batch = []
                current_char_count = 0

            current_batch.append(item)
            current_char_count += item_chars

        # Add any remaining items as a final batch
        if current_batch:
            batches.append(current_batch)

        if dropped_items:
            logger.warning(f"Dropped {len(dropped_items)} items due to exceeding max_chars.")

        # Ensure all items are accounted for
        total_in_batches = sum(len(batch) for batch in batches)
        if total_in_batches + len(dropped_items) != len(items):
            logger.error(f"Batching logic error: {len(items) - total_in_batches - len(dropped_items)} items unaccounted for.")

        return batches
  
