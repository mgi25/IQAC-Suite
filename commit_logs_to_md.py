import argparse
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Convert commit log file into grouped markdown file.")
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to file containing commit logs in 'YYYY-MM-DD | message' format",
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Path to output markdown file",
    )
    return parser.parse_args()


def read_logs(path: Path) -> dict:
    logs_by_date: dict[str, list[str]] = defaultdict(list)
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or "|" not in line:
                continue
            date_part, message = [part.strip() for part in line.split("|", 1)]
            if "Merge pull request" in message or "Merge branch" in message:
                continue
            logs_by_date[date_part].append(message)
    return logs_by_date


def write_markdown(logs_by_date: dict[str, list[str]], output: Path) -> None:
    with output.open("w", encoding="utf-8") as handle:
        for date in sorted(logs_by_date):
            handle.write(f"## {date}\n")
            for message in logs_by_date[date]:
                handle.write(f"- {message}\n")
            handle.write("\n")


def main() -> None:
    args = parse_args()
    logs_by_date = read_logs(args.input)
    write_markdown(logs_by_date, args.output)


if __name__ == "__main__":
    main()
