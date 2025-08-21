from regressionanalyser.analyzer.base_analyzer import BaseFailureAnalyzer
from regressionanalyser.prompts.api_failure_prompt import analyse_regression_failures_prompt as api_failure
from regressionanalyser.analyzer.failure_chain import FailureChain
from langchain_core.prompts import PromptTemplate

class APIFailureAnalyzer(BaseFailureAnalyzer):
    """
    Analyzer for API failures, which uses the APIFailureChain to handle
    the batching and parallel processing of failures.
    """

    prompt_template:PromptTemplate = api_failure
    max_failures_per_request :int= 5
    
    def _get_failure_chain(self):
        """Returns an instance of the specialized APIFailureChain."""
        return FailureChain(
            llm=self.llm,
            output_parser=self.output_parser,
            prompt_template=self.prompt_template,
            batch_size=self.batch_size,
            max_items_per_request= self.max_failures_per_request,
            mode="api"
        )