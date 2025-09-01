import os
from dotenv import load_dotenv, find_dotenv
from llm_wrappers.gemini_llm_model import GeminiModel
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

# Load environment variables
_ = load_dotenv(find_dotenv())

# Initialize LLM
gemini_llm = GeminiModel(
    model_name="gemini-2.0-flash",
    api_key=os.environ.get("GEMINI_API_KEY")
)

# In-memory dict to store histories by session_id
store = {}

def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# Prompt
prompt = PromptTemplate.from_template(
    "You are a chef. Suggest a famous dish from {location}."
)
parser = StrOutputParser()

# Chain
chain = prompt | gemini_llm | parser

# Wrap chain with message history
chain_with_memory = RunnableWithMessageHistory(
    chain,
    get_session_history,  # must be a callable that returns ChatMessageHistory
    input_messages_key="location",   # what field to track
    history_messages_key="chat_history",  # key for passing history into prompt
    output_messages_key="output",   # what to log from output
)

# Example usage
session_id = "abc123"

resp1 = chain_with_memory.invoke(
    {"location": "Hyderabad"},
    config={"configurable": {"session_id": session_id}}
)
print("Resp1:", resp1)

resp2 = chain_with_memory.invoke(
    {"location": "Telangana"},
    config={"configurable": {"session_id": session_id}}
)
print("Resp2:", resp2)
