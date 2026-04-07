import subprocess
import json
import os
import sys

KORDOC_PATH = r"C:\Antigravity\kordoc\dist\cli.js"

def parse_with_kordoc(file_path):
    """
    Parses a document using kordoc CLI and returns the JSON result.
    """
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"File not found: {abs_path}")

    # command: node C:\Antigravity\kordoc\dist\cli.js <file> --format json
    cmd = ["node", KORDOC_PATH, abs_path, "--format", "json"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error executing kordoc: {e.stderr}", file=sys.stderr)
        raise
    except json.JSONDecodeError as e:
        print(f"Failed to parse kordoc output as JSON: {e}", file=sys.stderr)
        raise
