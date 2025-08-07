from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import json
from dotenv import load_dotenv, find_dotenv

# Load environment variables
_ = load_dotenv(find_dotenv())

app = FastAPI()

# --- Your Project's Analysis Components ---
# Assuming these modules exist in your project structure
try:
    from regressionanalyser.parser.cucumber_parser import CucumberParser
    from regressionanalyser.analyzer.api_analyzer import APIFailureAnalyzer
    from regressionanalyser.parser.output_parser import CustomOutputParser, FailureAnalysisResult
    from llm_wrappers.claude_llm_model import ClaudeModel
    
    input_parser = CucumberParser()
    output_parser = CustomOutputParser(pydantic_object=FailureAnalysisResult)
    llm = ClaudeModel(model_name="claude-3-opus-20240229", api_key=os.environ.get("CLAUDE_API_KEY"))
    
    ui_analyzer = APIFailureAnalyzer(llm=llm, batch_size=4, output_parser=output_parser)
    api_analyzer = APIFailureAnalyzer(llm=llm, batch_size=4, output_parser=output_parser)
    analysis_components_ready = True
except ImportError as e:
    print(f"Warning: Missing analysis component import: {e}. Analysis endpoints may not function.")
    analysis_components_ready = False
except KeyError:
    print("Warning: CLAUDE_API_KEY not found in environment variables. LLM will not function.")
    analysis_components_ready = False
except Exception as e:
    print(f"Warning: Error initializing analysis components: {e}. Analysis endpoints may not function.")
    analysis_components_ready = False

# --- IMPORTANT: Correct Path to Static Files ---
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

# In-memory storage for results (will be overwritten on new uploads)
current_results_data = []

@app.post("/upload-cucumber-report/")
async def upload_cucumber_report(file: UploadFile = File(...), report_type: str= "UI Report"):
    """Uploads a Cucumber report, analyzes it, and saves results."""
    if not analysis_components_ready:
        return JSONResponse(status_code=500, content={"message": "Analysis components not initialized."})
    try:
        contents = await file.read()
        report_data = json.loads(contents)
        if report_type=="API Report":
            results =  ui_analyzer.analyzeReport(report_data)
        else:
            results  = api_analyzer.analyzeReport(report_data)
            
        serializable_results = [r.model_dump() for r in results]
        
        with open("results.json", "w") as f:
            json.dump(serializable_results, f, indent=2)
        
        return JSONResponse(content={"message": "Report analyzed and results saved successfully!"})
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"message": "Invalid JSON file."})
    except Exception as e:
        print(f"Error during report upload: {e}")
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serves the dashboard's HTML page."""
    with open("dashboard/static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/results")
async def get_results_data():
    """Provides the analyzed results as JSON."""
    try:
        with open("results.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []
    return JSONResponse(content=data)

# To run this app: uvicorn dashboard.app:app --reload