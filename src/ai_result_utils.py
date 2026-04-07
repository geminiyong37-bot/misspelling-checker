import json
import os

def load_ai_result(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def ai_errors_to_rows(ai_result):
    errors = ai_result.get("errors", [])
    source = ai_result.get("source") or "알 수 없는 문서"
    
    rows = []
    for err in errors:
        rows.append({
            "file": source,
            "page": err.get("page", 1),
            "original": err.get("original", ""),
            "corrected": err.get("corrected", ""),
            "help": err.get("reason", ""),
            "errorType": err.get("errorType")
        })
    return rows
