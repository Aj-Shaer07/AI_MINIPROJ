"""Simple health check script for the backend.

Usage:
    python health_check.py
Exits with code 0 if /health returns {"status":"ok"}, non-zero otherwise.
"""
import sys
import json
from urllib.request import urlopen


def main():
    url = "http://127.0.0.1:8000/health"
    try:
        with urlopen(url, timeout=5) as resp:
            data = json.load(resp)
            if data.get("status") == "ok":
                print("healthy")
                return 0
            else:
                print("unexpected response:", data)
                return 2
    except Exception as e:
        print("health check failed:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
