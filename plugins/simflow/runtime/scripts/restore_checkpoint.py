#!/usr/bin/env python3
"""Restore workflow state from a checkpoint."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.checkpoint import restore_checkpoint, list_checkpoints


def main():
    parser = argparse.ArgumentParser(description="Restore checkpoint")
    parser.add_argument("--checkpoint-id", help="Checkpoint ID to restore")
    parser.add_argument("--latest", action="store_true", help="Restore latest checkpoint")
    parser.add_argument("--list", action="store_true", help="List available checkpoints")
    parser.add_argument("--base-dir", default=".", help="Base directory")
    args = parser.parse_args()

    if args.list:
        ckpts = list_checkpoints(args.base_dir)
        print(json.dumps(ckpts, indent=2))
        return

    if args.latest:
        ckpts = list_checkpoints(args.base_dir)
        if not ckpts:
            print(json.dumps({"status": "error", "message": "No checkpoints found"}))
            sys.exit(1)
        ckpt_id = ckpts[-1]["checkpoint_id"]
    elif args.checkpoint_id:
        ckpt_id = args.checkpoint_id
    else:
        print(json.dumps({"status": "error", "message": "Specify --checkpoint-id or --latest"}))
        sys.exit(1)

    try:
        ckpt = restore_checkpoint(ckpt_id, args.base_dir)
        print(json.dumps({"status": "success", "checkpoint": ckpt}, indent=2))
    except FileNotFoundError as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
