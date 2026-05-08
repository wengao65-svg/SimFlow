#!/usr/bin/env python3
"""Write data to a .simflow/state/ file."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.state import write_state


def main():
    parser = argparse.ArgumentParser(description="Write SimFlow state")
    parser.add_argument("--file", required=True, help="State file name")
    parser.add_argument("--data", required=True, help="JSON data to write")
    parser.add_argument("--base-dir", default=".", help="Base directory")
    args = parser.parse_args()

    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "message": f"Invalid JSON: {e}"}))
        sys.exit(1)

    path = write_state(data, args.base_dir, args.file)
    print(json.dumps({"status": "success", "path": str(path)}))


if __name__ == "__main__":
    main()
