from typing import List, Dict, Any
from abc import ABC, abstractmethod

class BaseParser(ABC):
    """
    Abstract base class for all report parsers.
    """

    @abstractmethod
    def extract_failures(self, report_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extracts raw failures from the report data.
        """
        pass

    @abstractmethod
    def structure_failure(self, failure: Dict[str, Any]) -> Dict[str, Any]:
        """
            Structures a raw failure into a standardized format.
        """
        pass