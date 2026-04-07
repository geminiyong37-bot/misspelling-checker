import json
import os
import re

def load_ai_result(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def ai_errors_to_rows(ai_result):
    errors = ai_result.get("errors", [])
    
    # 출처 설정: source -> metadata.title -> 기본값 순서
    source = ai_result.get("source")
    if not source:
        metadata = ai_result.get("metadata") or {}
        source = metadata.get("title") or "알 수 없는 문서"
    
    rows = []
    for err in errors:
        reason = err.get("reason") or err.get("meta", "설명 없음")
        # "맞춤법 오류: ", "띄어쓰기 오류: " 등 한국어 접두사 제거
        reason = re.sub(r'^(맞춤법|띄어쓰기|표기|문장)\s*오류:\s*', '', reason)
        
        rows.append({
            "file": source,
            "page": err.get("page", 1),
            "original": err.get("original", ""),
            "corrected": err.get("corrected", ""),
            "help": reason,
            "errorType": err.get("errorType")
        })
    return rows
