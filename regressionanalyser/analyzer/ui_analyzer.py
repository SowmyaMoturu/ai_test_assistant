from typing import Any, Callable, Dict, List
from concurrent.futures import ThreadPoolExecutor
from langchain_core.messages import HumanMessage
from regressionanalyser.analyzer.base_analyzer import  BaseFailureAnalyzer
from regressionanalyser.analyzer.failure_chain import FailureChain

from regressionanalyser.prompts.ui_failure_prompt import analyse_regression_failures_prompt as ui_failure



class UIFailureAnalyzer(BaseFailureAnalyzer):
    """Analyzer for UI failures with screenshots"""

    prompt_func :callable = ui_failure

    def _get_failure_chain(self):
        return FailureChain(
            llm=self.llm,
            output_parser=self.output_parser,
            prompt_func=self.prompt_func,
            batch_size=self.batch_size,
            mode='ui'
        )