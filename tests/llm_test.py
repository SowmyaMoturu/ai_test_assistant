import os
from dotenv import find_dotenv, load_dotenv
from llm_wrappers.gemini_llm_model import GeminiModel
from llm_wrappers.opeai_llm_model import OpenAIChatModel
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


# Load environment variables
_ = load_dotenv(find_dotenv())

# Initialize LLMs
gemini_llm = GeminiModel(model_name="gemini-2.0-flash", api_key=os.environ.get("GEMINI_API_KEY"))
openai_llm = OpenAIChatModel(model_name="gpt-4o", api_key=os.environ.get("OPENAI_API_KEY"))

### Example: Get classic dish from a location
template = """
Your job is to come up with a classic dish from the area that user suggests.
Location: {location}

Respond only with the name of the dish
"""

template1 = """
You are a culinary expert. Provide recipe to the dish name provided
Dish Name: {dish_name}

Respond only with the recipe of the dish
"""

# Use StrOutputParser to get string content
parser = StrOutputParser()

prompt_template = PromptTemplate.from_template(template=template)
prompt_template1 = PromptTemplate.from_template(template=template1)
chain = prompt_template | gemini_llm | parser 

print(chain.invoke({"location": "Telangana"}))
