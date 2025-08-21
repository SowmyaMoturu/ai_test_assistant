from fastapi import FastAPI, File, UploadFile
from fastapi.params import Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import json
import pandas as pd
from dotenv import load_dotenv, find_dotenv
import logging
from regressionanalyser.parser.cucumber_parser import CucumberParser
from regressionanalyser.analyzer.api_analyzer import APIFailureAnalyzer
from regressionanalyser.parser.output_parser import CustomOutputParser, FailureAnalysisResult
from llm_wrappers.claude_llm_model import ClaudeModel

from llm_wrappers.gemini_llm_model import GeminiModel
from regressionanalyser.analyzer.ui_analyzer import UIFailureAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables    s
_ = load_dotenv(find_dotenv())

app = FastAPI()

# --- Your Project's Analysis Components ---
# Assuming these modules exist in your project structure
try:
    
    
    input_parser = CucumberParser()
    output_parser = CustomOutputParser(pydantic_object=FailureAnalysisResult)
    llm = GeminiModel(model_name="gemini-2.0-flash", api_key=os.environ.get("GEMINI_API_KEY"))
    
    ui_analyzer = UIFailureAnalyzer(llm=llm, batch_size=4, output_parser=output_parser)
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
async def upload_cucumber_report(file: UploadFile = File(...), report_type: str= Form("api")):
    logger.info(f"Received file upload: {file.filename}, type: {report_type}")
    """Uploads a Cucumber report, analyzes it, and saves results."""
    if not analysis_components_ready:
        return JSONResponse(status_code=500, content={"message": "Analysis components not initialized."})
    try:
        contents = await file.read()
        report_data = json.loads(contents)
        if report_type == "ui":
            results = ui_analyzer.analyzeReport(report_data)
        else:
            results = api_analyzer.analyzeReport(report_data)

        # Type check: handle string or error result
        if isinstance(results, str):
            return JSONResponse(status_code=500, content={"message": f"Analyzer returned error: {results}"})
        if not isinstance(results, list):
            return JSONResponse(status_code=500, content={"message": "Analyzer did not return a list of results."})

        # Flatten results if any sublists exist
        flat_results = []
        for r in results:
            if isinstance(r, list):
                flat_results.extend(r)
            else:
                flat_results.append(r)
        serializable_results = []
        validation_errors = []
        for item in flat_results:
            try:
                if hasattr(item, 'dict'):
                    serializable_results.append(item.dict())
                elif hasattr(item, 'model_dump'):
                    serializable_results.append(item.model_dump())
                elif isinstance(item, dict):
                    serializable_results.append(item)
                else:
                    raise ValueError(f"Unexpected result type: {type(item)}")
            except Exception as ve:
                validation_errors.append(str(ve))

        if validation_errors:
            logger.error(f"LLM response validation errors: {validation_errors}")
            return JSONResponse(status_code=500, content={
                "message": "Some results could not be parsed or validated.",
                "errors": validation_errors,
                "raw_results": [str(item) for item in flat_results]
            })

        with open("results.json", "w") as f:
            json.dump(serializable_results, f, indent=2)

        return JSONResponse(content={"message": "Report analyzed and results saved successfully!"})
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"message": "Invalid JSON file."})
    except Exception as e:
        logger.error(f"Error during report upload: {e}")
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})


# Entry page now serves summary
@app.get("/", response_class=HTMLResponse)
async def entry_page():
    with open("dashboard/static/summary.html", "r") as f:
        return HTMLResponse(content=f.read())

# Details page
@app.get("/details", response_class=HTMLResponse)
async def get_details():
    with open("dashboard/static/details.html", "r") as f:
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


# --- Summary Metrics Endpoint ---
@app.get("/api/summary-metrics")
async def get_summary_metrics():
    try:
        with open("results.json", "r") as f:
            test_results = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return JSONResponse(content={})

    df = pd.DataFrame(test_results)

    # Feature failure analysis
    feature_stats = df.groupby(["feature_name"]).size()
    feature_failures = [
        {"feature": feature, "failed": int(count)}
        for feature, count in feature_stats.items()
    ]
    feature_failures.sort(key=lambda x: x["failed"], reverse=True)

    # Step failure analysis
    step_stats = {}
    for _, row in df.iterrows():
        step_key = row.get("step_details") or "Unknown Step"
        if step_key not in step_stats:
            step_stats[step_key] = {"count": 0, "features": set(), "files": set()}
        step_stats[step_key]["count"] += 1
        step_stats[step_key]["features"].add(row.get("feature_name"))
        step_stats[step_key]["files"].add(row.get("file_path"))
    step_failures = [
        {
            "step": step,
            "count": stats["count"],
            "affectedFeatures": len(stats["features"]),
            "affectedFiles": len(stats["files"]),
            "features": list(stats["features"]),
            "files": list(stats["files"])
        }
        for step, stats in step_stats.items()
    ]
    step_failures.sort(key=lambda x: x["count"], reverse=True)

    # Error pattern analysis
    error_patterns = {}
    for _, row in df.iterrows():
        error_type = str(row.get("error_message", "Unknown Error")).split(":")[0] or "Unknown Error"
        if error_type not in error_patterns:
            error_patterns[error_type] = {"count": 0, "features": set()}
        error_patterns[error_type]["count"] += 1
        error_patterns[error_type]["features"].add(row.get("feature_name"))
    error_type_failures = [
        {
            "errorType": error,
            "count": stats["count"],
            "affectedFeatures": len(stats["features"])
        }
        for error, stats in error_patterns.items()
    ]
    error_type_failures.sort(key=lambda x: x["count"], reverse=True)

    return JSONResponse(content={
        "featureFailures": feature_failures,
        "stepFailures": step_failures,
        "errorTypeFailures": error_type_failures
    })

# --- Serve summary.html ---
@app.get("/summary", response_class=HTMLResponse)
async def get_summary():
    with open("dashboard/static/summary.html", "r") as f:
        return HTMLResponse(content=f.read())
    
    # To run this app: uvicorn dashboard.app:app --reload