from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel
from langchain_community.llms import BaseLLM
from regressionanalyser.analyzer.failure_chain import FailureChain
from regressionanalyser.parser.base_parser import BaseParser
from regressionanalyser.parser.cucumber_parser import CucumberParser
from regressionanalyser.parser.output_parser import CustomOutputParser, FailureAnalysisResult
from regressionanalyser.utils.report_ingestor import download_report_from_s3
from langchain.output_parsers import PydanticOutputParser

class BaseFailureAnalyzer(ABC, BaseModel):

    llm: BaseLLM
    input_parser :BaseParser = CucumberParser()
    output_parser:CustomOutputParser = CustomOutputParser(pydantic_object=FailureAnalysisResult)
    batch_size :int= 25
    max_failures_per_request :int= 1

    model_config = {
        "arbitrary_types_allowed": True
    }
    

    def load_report(self, report_path: str, app_code: str = None) -> List[Dict[str, Any]]:
        return download_report_from_s3(report_path, app_code)
        

    @abstractmethod
    def _get_failure_chain(self)->FailureChain:
        """Get the appropriate failure chain for this analyzer type"""
        pass

    def analyzeReport(self, report_data: List[Dict[str, Any]]) -> List[Any]:
        failures = self.input_parser.extract_failures(report_data)
        structured_failures = [self.input_parser.structure_failure(f) for f in failures]
        
        failure_chain = self._get_failure_chain()
        return failure_chain.run(structured_failures)
    
    def analyzeS3Report(self, report_path:str, app_code:str) -> List[Any]:
        report_data = self.load_report(report_path,app_code)
        return self.analyzeReport(report_data)