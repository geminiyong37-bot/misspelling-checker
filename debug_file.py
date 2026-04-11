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
    print("Parsing successful.")
    
    print("Building doc model...")
    doc = build_doc_from_parse_result(raw, f_path)
    print(f"Total sentences: {len(doc.get('sentences', []))}")
    
    # Check if any sentence is weird
    for i, s in enumerate(doc.get('sentences', [])[:5]):
        print(f"Sample {i}: {s.get('text')[:50]}...")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
