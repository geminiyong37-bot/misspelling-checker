import sys
import os

# Add src to path if needed for local imports
sys.path.append(os.path.dirname(__file__))

from ai_client import (
    validate_api_key, 
    PROVIDER_GEMINI, PROVIDER_OPENAI, PROVIDER_ANTHROPIC,
    detect_provider
)

def main():
    if len(sys.argv) < 2:
        print("Usage: verify_key.exe <api_key> [provider]")
        sys.exit(1)

    api_key = sys.argv[1].strip()
    
    # If provider is not provided, detect it
    if len(sys.argv) > 2:
        provider = sys.argv[2].lower()
    else:
        provider = detect_provider(api_key)

    # Validate
    success, message = validate_api_key(api_key, provider)
    
    if success:
        print(f"SUCCESS: {provider}")
        sys.exit(0)
    else:
        # Categorize error for installer
        if "유효하지 않은" in message or "invalid" in message.lower() or "401" in message:
            print(f"FAILURE_KEY: {message}", file=sys.stderr)
            sys.exit(2)  # Invalid Key
        else:
            print(f"FAILURE_NET: {message}", file=sys.stderr)
            sys.exit(3)  # Network or other error

if __name__ == "__main__":
    main()
