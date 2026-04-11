import json
import os
import sys

# Add src to path
sys.path.append(os.getcwd())

from src.hwp_parser import parse_with_kordoc
from src.doc_model import build_doc_from_parse_result

f_path = r"c:\Antigravity\misspelling-checker\test docs\2022년개교예정사이버대학설립요령(공지용).hwp"

print("Parsing...")
try:
    raw = parse_with_kordoc(f_path)
    doc = build_doc_from_parse_result(raw, f_path)
    sentences = doc.get("sentences", [])
    print(f"Total sentences: {len(sentences)}")
    
    bad_chars = 0
    for idx, s in enumerate(sentences):
        text = s.get("text", "")
        # Check for control characters (except newline, carriage return, tab)
        if any(ord(c) < 32 and c not in '\n\r\t' for c in text):
            print(f"Found bad char in sentence {idx}: {repr(text)}")
            bad_chars += 1
        # Check for extremely long sentences
        if len(text) > 2000:
            print(f"Extremely long sentence {idx}: {len(text)} chars")
            
    print(f"Scanning complete. Bad char sentences: {bad_chars}")

except Exception as e:
    print(f"FAILED: {e}")
