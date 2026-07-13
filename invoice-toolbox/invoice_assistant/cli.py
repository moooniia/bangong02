import argparse
import json
from pathlib import Path

from .safe_party_parser import parse_party_fields


def main() -> int:
    parser = argparse.ArgumentParser(description="Invoice Assistant 2 tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_party = subparsers.add_parser("parse-party", help="Parse buyer/seller fields safely")
    parse_party.add_argument("text_file", type=Path, help="OCR text file to parse")

    args = parser.parse_args()
    if args.command == "parse-party":
        lines = args.text_file.read_text(encoding="utf-8").splitlines()
        parsed = parse_party_fields(lines)
        print(json.dumps(parsed.as_dict(), ensure_ascii=False, indent=2))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

