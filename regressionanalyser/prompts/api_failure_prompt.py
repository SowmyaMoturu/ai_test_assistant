from langchain_core.prompts import PromptTemplate

api_failure_template = """
Analyze the error message to determine the reason for the failure.

Error Details: {failure_details}

Generate a JSON object representing the following information based on the error details and screenshot analysis.

The output should be valid JSON and should not contain unnecessary escape characters.

File Path Handling:
Return only the portion of the file path starting from 'src'. If the path doesn't contain 'src', use 'other'.

Error Category Determination Logic:
- Test Data Issue: Classify as "Test Data Issue" if the detailed_error_message contains phrases like "The assertion failed because the specified customer," "the specified customer could not be found," or if a screenshot indicates a data validation error that prevented an API call or other action.
- Script Issue: Classify as "Script Issue" if the detailed_error_message contains "could not be found within the specified timeout" or other indications of element timing issues, incorrect locators, or problems with the test script's logic. Also classify as "Script Issue" if page.waitForResponse timed out but the UI appears to have loaded correctly according to the screenshot, suggesting the script is waiting for the wrong network event.
- Environment Issue: Classify as "Environment Issue" if the detailed_error_message contains "page.waitForResponse timeout exceeded" AND the screenshot shows signs of environmental problems like a persistent loader, a generic "something went wrong" message, a reload button, or a blank page.
- Other Issue: If failure file path is not on project root, classify as other.

Important Considerations:
* Provide detailed and actionable insights.
* Return ONLY Array of the JSON object, no extra text or information.
* handle all escape chracters, should be able to parse json without cleanup

{format_instructions}
"""

analyse_regression_failures_prompt = PromptTemplate.from_template(api_failure_template)