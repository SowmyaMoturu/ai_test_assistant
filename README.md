# Failure Analyzer

A modular Python tool for analyzing and categorizing Cucumber test failures using Large Language Models (LLMs) such as Gemini or Claude. Designed for extensibility, batch processing, and integration with CI/CD pipelines.

## Features

- **Cucumber JSON report ingestion** (local or S3)
- **Failure extraction and structuring**
- **Prompt-based LLM analysis** (customizable for UI/API or report format)
- **Batch and parallel processing via unified chain logic**
- **Deduplication support**
- **Modular input/output parsing**
- **Secure API key handling via environment variables**
- **Extensible chain architecture for auto-fixing, refactoring, and more**

## Usage

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Prepare your environment

- Set your LLM API key as an environment variable (recommended for CI/CD):
  ```bash
  export LLM_API_KEY=your-api-key
  ```

### 3. Run the analyzer

#### CLI Mode (for jobs/integration)
```bash
python regressionanalyzer/main.py <s3_report_path> <environment> <report_type> [local_report_path]
```
- `s3_report_path`: S3 path to the Cucumber report (or `None` for local only)
- `environment`: Environment name (e.g., SIT, PROD)
- `report_type`: Report type (e.g., cucumber)
- `local_report_path`: (Optional) Local path to save/download the report

#### Local Testing (no CLI)
Edit `main.py` to set values directly for quick local runs.

### 4. Output

Results are pushed to a database to dispaly on dashboard

## Project Structure

```
regressionanalyser/
│
├── analyzer/
│   ├── base_analyzer.py
│   ├── api_analyzer.py
│   ├── ui_analyzer.py
│   └── failure_chain.py
├── parser/
│   ├── cucumber_parser.py
│   └── output_parser.py
├── prompts/
│   ├── api_failure_prompt.py
│   └── ui_failure_prompt.py
├── utils/
│   └── report_ingestor.py
llm_chains/
│   └── base_chain.py
failure-analyzer/
│   └── main.py
requirements.txt
README.md
```

## Chain Architecture

- **llm_chains/base_chain.py**: Provides generic batching, LLM input preparation, and parallel processing logic.
- **analyzer/failure_chain.py**: Specializes chain logic for failure analysis (handles screenshots, batching, etc.).
- **Extendable**: You can create new chains for auto-fixing, refactoring, etc., by inheriting from `BaseChain`.

## Extending

- Add new report parsers in `parser/`
- Add new LLM wrappers in `llm_wrappers/`
- Add new prompt templates in `prompts/`
- Customize output parsing in `parser/output_parser.py`
- Create new chains for other intelligent test maintenance tasks by extending `BaseChain`

---

## Dashboard (Web UI)

The dashboard is an **additional feature** for uploading, processing, and visualizing analysis results.

### How to use the dashboard

1. **Start the backend:**
   ```bash
   uvicorn dashboard.app:app --reload
   ```

2. **Open the dashboard:**
   Visit [http://localhost:8000](http://localhost:8000) in your browser.

3. **Upload and process reports:**
   - Select **Report Type** (UI/API) from the dropdown.
   - Upload your `results.json` file.
   - Click **Process** to analyze and update the dashboard.

4. **Explore results:**
   - View all failures in a modern table.
   - Click "+" to expand each row for possible causes and recommended fixes.

---


**For questions or contributions, open an issue