import subprocess
import json
import os
import sys

def resource_path(relative):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative)

# 개발 환경에서는 상위 레벨의 kordoc을 바로 참조하고, 빌드된 환경에서는 복사된 _MEIPASS 내의 kordoc 참조
if hasattr(sys, '_MEIPASS'):
    KORDOC_PATH = resource_path(os.path.join("kordoc", "dist", "cli.js"))
    # 빌드된 환경(frozen)에서는 세트로 묶인 node.exe 사용
    NODE_EXE_PATH = resource_path(os.path.join("bin", "node.exe"))
else:
    KORDOC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "kordoc", "dist", "cli.js"))
    NODE_EXE_PATH = "node" # 개발 환경에서는 전역 node 사용


def parse_with_kordoc(file_path):
    """
    Parses a document (HWP, HWPX, PDF, DOCX) using kordoc CLI, 
    or reads directly if it's a plain text files (.txt).
    """
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"File not found: {abs_path}")

    ext = os.path.splitext(abs_path)[1].lower()

    # 1. Plain text handling
    if ext == '.txt':
        content = ""
        # Try utf-8 first, fallback to cp949
        for enc in ['utf-8', 'cp949', 'euc-kr']:
            try:
                with open(abs_path, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        
        # Build kordoc-compatible JSON structure
        return {
            "blocks": [
                {
                    "type": "paragraph",
                    "text": content,
                    "pageNumber": 1
                }
            ],
            "fileType": "txt"
        }

    # 2. kordoc CLI handling (HWP, HWPX, PDF, DOCX)
    # command: node C:\Antigravity\kordoc\dist\cli.js <file> --format json
    cmd = [NODE_EXE_PATH, KORDOC_PATH, abs_path, "--format", "json"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=True)
        stdout = result.stdout
        
        # Extract JSON part (in case kordoc prints progress to stdout)
        start_idx = stdout.find('{')
        end_idx = stdout.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_str = stdout[start_idx:end_idx + 1]
            return json.loads(json_str)
        else:
            return json.loads(stdout) # Fallback to original
    except subprocess.CalledProcessError as e:
        # kordoc might exit with error for unsupported formats like .doc
        error_msg = e.stderr or e.stdout
        print(f"Error executing kordoc: {error_msg}", file=sys.stderr)
        raise Exception(f"문서 파싱 실패 (kordoc): {error_msg}")
    except json.JSONDecodeError as e:
        print(f"Failed to parse kordoc output as JSON: {e}", file=sys.stderr)
        raise
