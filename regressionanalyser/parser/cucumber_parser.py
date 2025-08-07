from typing import Dict, List, Any
import re
import logging

from regressionanalyser.parser.base_parser import BaseParser

logger = logging.getLogger("CucumberParser")

class CucumberParser(BaseParser):
    def extract_failures(self, cucumber_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        failures = []
        logger.info("Extracting failures from Cucumber report.")

        for feature in cucumber_data:
            for scenario in feature.get('elements', []):
                for step in scenario.get('steps', []):
                    if step.get('result', {}).get('status') == "failed":
                        after_step = scenario.get('steps', [])[-1]
                        failure = {
                            'feature': feature.get('name'),
                            'scenario': scenario.get('name'),
                            'step': step.get("name"),
                            'error_message': step.get('result', {}).get('error_message'),
                            'embeddings': after_step.get('embeddings', [])
                        }
                        failures.append(failure)
        logger.info(f"Found {len(failures)} failed scenarios.")
        return failures

    def structure_failure(self, failure: Dict[str, Any]) -> Dict[str, Any]:
        structured_failure = {
            'error_message': failure['error_message'],
            'step_details': failure['step'],
            'feature_name': f"{failure['feature']}",
            'scenario_name': f"{failure['scenario']}",
            'file_path': self._extract_file_path(failure['error_message']),
            'line_number': self._extract_line_number(failure['error_message']),
            'screenshot': self.extract_screenshot(failure.get('embeddings', []))
        }
        return structured_failure

    def extract_screenshot(self, embeddings: List[Dict[str, str]]) -> str:
        for embedding in embeddings:
            if embedding.get('mime_type') == 'image/png':
                return embedding.get('data', '')
        return ""

    def _extract_file_path(self, error_message: str) -> str:
        match = re.search(r'at (.+?):', error_message)
        return match.group(1) if match else ""

    def _extract_line_number(self, error_message: str) -> str:
        match = re.search(r':(\d+)', error_message)
        return match.group(1) if match else ""