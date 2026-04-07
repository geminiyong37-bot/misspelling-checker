import argparse
import json
import os
import sys
from hwp_parser import parse_with_kordoc
from doc_model import build_doc_from_parse_result
from ai_client import run_gemini_check
from excel_exporter import export_to_excel, build_rows_from_doc
from ai_result_utils import load_ai_result, ai_errors_to_rows

def main():
    parser = argparse.ArgumentParser(description="Misspelling Checker (Python)")
    parser.add_argument("files", nargs="*", help="Files to parse")
    parser.add_argument("--out", "-o", help="Output JSON path")
    parser.add_argument("--ai", action="store_true", help="Run AI check")
    parser.add_argument("--excel", help="Output Excel path")
    
    args = parser.parse_args()

    if not args.files and not args.ai:
        parser.print_help()
        sys.exit(1)

    all_results = []

    for file_path in args.files:
        try:
            print(f"파싱 중: {file_path}")
            raw_result = parse_with_kordoc(file_path)
            doc = build_doc_from_parse_result(raw_result, file_path)
            
            if args.ai:
                print("AI 오타 검증 시작…")
                errors = run_gemini_check(doc)
                payload = {
                    "source": doc["file"],
                    "metadata": doc.get("metadata"),
                    "errors": errors,
                    "generatedAt": doc.get("generatedAt")
                }
                all_results.append(payload)
                
                if args.out:
                    with open(args.out, "w", encoding="utf-8") as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)
                    print(f"AI 결과 저장 완료: {args.out}")
            else:
                if args.out:
                    with open(args.out, "w", encoding="utf-8") as f:
                        json.dump(doc, f, ensure_ascii=False, indent=2)
                    print(f"파싱 결과 저장 완료: {args.out}")
                else:
                    print(json.dumps(doc, ensure_ascii=False, indent=2))
                    
            if args.excel:
                print(f"엑셀 파일 생성 중: {args.excel}")
                if args.ai:
                    # AI 결과를 엑셀로 변환
                    rows = ai_errors_to_rows(payload)
                    export_to_excel(rows, args.excel)
                else:
                    # 파싱 결과만 엑셀로 변환
                    rows = build_rows_from_doc(doc)
                    export_to_excel(rows, args.excel)
                print(f"엑셀 저장 완료: {args.excel}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
