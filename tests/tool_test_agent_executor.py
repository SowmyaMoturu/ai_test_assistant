import os
from dotenv import load_dotenv, find_dotenv
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

# Load environment variables
load_dotenv(find_dotenv())

# -------------------------
# 1. LLM initialization
# -------------------------
from llm_wrappers.gemini_llm_model import GeminiModel
from llm_wrappers.opeai_llm_model import OpenAIChatModel

# Initialize LLMs (using OpenAI's GPT-4o by default for better performance)
llm = GeminiModel(
    model_name="gemini-1.5-flash",
    api_key=os.environ.get("GEMINI_API_KEY")
)
openai_llm = OpenAIChatModel(model_name="gpt-4o", api_key=os.environ.get("OPENAI_API_KEY"))

# -------------------------
# 2. Define Tools
# -------------------------
@tool
def quiz_me(subject: str) -> str:
    """Generate a quiz question for the given subject."""
    quiz_bank = {
        "science": [
            "What is the chemical symbol for water?",
            "What planet is known as the Red Planet?",
            "What is photosynthesis?"
        ],
        "biology": [
            "What is the powerhouse of the cell?",
            "What molecule carries genetic information?"
        ],
        "chemistry": [
            "What is the chemical formula for table salt?",
            "What is the pH of pure water?"
        ],
        "physics": [
            "What is Newton's second law?",
            "What is the speed of light?"
        ],
        "math": [
            "What is 12 * 8?",
            "What is the square root of 144?",
            "What is 10 to the power of 3?"
        ]
    }
    
    # Normalize the subject
    subject = subject.lower()

    # Fallback for science subtopics
    if subject == "science":
        return quiz_bank["science"][0]  # pick first question for simplicity

    # Pick question if subject exists
    return quiz_bank.get(subject, ["Sorry, no quiz available for this subject."])[0]


@tool
def summarize(text: str) -> str:
    """Summarize the given text in a few sentences."""
    return text[:150] + "..." if len(text) > 150 else text


@tool
def search_in_wiki(query: str) -> str:
    """Search Wikipedia-like content and return a short answer."""
    wiki_db = {
        "photosynthesis": "Photosynthesis is the process by which green plants use sunlight to synthesize foods from CO2 and water.",
        "mars": "Mars is the fourth planet from the Sun, often called the Red Planet."
    }
    return wiki_db.get(query.lower(), "No result found in wiki.")

# -------------------------
# 3. Prompt Template
# -------------------------
# The prompt now includes a complete example of a successful ReAct chain,
# including the Observation and Final Answer to guide the LLM's output.
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are StudyBuddy. You have access to the following tools: {tool_names}.\n"
     "You must use a tool to answer the user's request. Strictly follow the exact format:\n"
     "Thought: <your reasoning>\n"
     "Action: <tool name>\n"
     "Action Input: <input to tool>\n"
     "Then, the tool will execute. The result of the tool will be provided to you as an 'Observation'.\n"
     "If you have the final answer, use the format:\n"
     "Thought: <your reasoning>\n"
     "Final Answer: <the final answer>\n"
     "Reason using {agent_scratchpad}. Do not make up answers.\n"
     "Tool details: {tools}\n"
     "Here is a complete example of a successful quiz question workflow:\n"
     "User: quiz me on science\n"
     "Thought: The user wants a quiz question on science. The 'quiz_me' tool can be used for this purpose.\n"
     "Action: quiz_me\n"
     "Action Input: science\n"
     "Observation: What is the chemical symbol for water?\n"
     "Thought: The tool provided the quiz question. This is the final answer.\n"
     "Final Answer: What is the chemical symbol for water?\n"),
    ("user", "{input}"),
    ("assistant", "{agent_scratchpad}")
])

# -------------------------
# 4. Create Agent
# -------------------------
tools = [quiz_me, summarize, search_in_wiki]

# Use the more reliable openai_llm by default
agent = create_react_agent(
    llm=openai_llm,
    tools=tools,
    prompt=prompt
)

# Define a custom error handler to terminate the loop
def handle_parse_error(e: Exception) -> str:
    """
    Handles parsing errors by returning a user-friendly message.
    This prevents the agent from getting stuck in a retry loop.
    """
    return f"I'm sorry, I couldn't process the request due to a formatting error. Please try again. Error: {e}"


agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    # Use the custom function to gracefully handle errors and terminate the loop
    handle_parsing_errors=handle_parse_error,
    # Set a low max_iterations as a fail-safe
    max_iterations=5
)

# -------------------------
# 5. Run Agent
# -------------------------
if __name__ == "__main__":
    subject = "math"
    result = agent_executor.invoke({"input": f"Who is Agatha Christie?"})
    print("\n🤖 StudyBuddy:", result["output"])
