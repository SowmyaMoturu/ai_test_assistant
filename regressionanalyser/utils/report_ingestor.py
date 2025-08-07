import json

def download_report_from_s3():
    with open("cucumber_report.json", "r") as f:
        return json.load(f)