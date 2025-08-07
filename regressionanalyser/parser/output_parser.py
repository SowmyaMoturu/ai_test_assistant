from jsonschema import ValidationError
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from typing import List, Any
import json
import re
from langchain_core.outputs import Generation

class FailureAnalysisResult(BaseModel):
    """
    Pydantic model representing a single analyzed test failure result.
    Matches the structure you provided.
    """
    detailed_reason: str = Field(..., description="Detailed reason for the failure.")
    error_message: str = Field(..., description="The raw error message from the test.")
    squad_name: str = Field(..., description="Name of the squad responsible for the feature.")
    possible_causes: List[str] = Field(..., description="List of possible causes for the failure.")
    recommended_fixes: List[str] = Field(..., description="List of recommended fixes for the failure.")
    feature_name: str = Field(..., description="Name of the feature under test.")
    scenario_name: str = Field(..., description="Name of the specific scenario that failed.")
    step_details: str = Field(..., description="Details of the test step where the failure occurred.")
    file_path: str = Field(..., description="Path to the test file.")
    line_number: str = Field(..., description="Line number in the test file where the failure occurred.")

class CustomOutputParser(PydanticOutputParser, BaseModel):
    def parse(self, text: str) -> FailureAnalysisResult:
        parsed_data = super().parse(text)
        return FailureAnalysisResult(**parsed_data)

    def parse_multiple(self, texts: List[str]) -> List[FailureAnalysisResult]:
        return [self.parse(text) for text in texts]
    

    def parse_result(self, result: List[Generation], *, partial: bool = False) -> Any:
        # Check if result is a list and has at least one item.
        if not result or not isinstance(result, list):
            raise ValueError("Expected a list of Generation objects.")

        llm_output_text = result[0].text
        
        # --- NEW CODE: Strip markdown fences ---
        # The regex pattern will match and remove the '```json' and '```' fences.
        llm_output_text = re.sub(r"```json\s*|```\s*$", "", llm_output_text, flags=re.DOTALL).strip()
        # --- END OF NEW CODE ---
        
        try:
            parsed_data = json.loads(llm_output_text)
            
            if isinstance(parsed_data, list):
                # If it's a list, validate each item.
                return [self.pydantic_object.model_validate(item) for item in parsed_data]
            else:
                # If it's a single dict, validate and wrap in a list.
                validated_item = self.pydantic_object.model_validate(parsed_data)
                return alidated_item
        except (json.JSONDecodeError, ValidationError) as e:
            # Re-raising the error with the cleaned text for better debugging.
            raise ValueError(
                f"Could not parse LLM output as JSON. Output was:\n{llm_output_text}\nError: {e}"
            ) from e
