#!/usr/bin/env python3

import argparse
import re
import unicodedata
from pathlib import Path


EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def normalize_text(value: str) -> str:
    value = value.strip()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = value.replace("'", "")
    value = re.sub(r"[^a-z0-9@._,\-;|+ ]", "", value)
    return value.strip()


def clean_token(token: str) -> str:
    return re.sub(r"[\s.\-_\+]+", "", token or "")


def is_email(value: str) -> bool:
    return bool(EMAIL_REGEX.match(value.strip().lower()))


def split_email_localpart(localpart: str):
    """
    Try to infer first/last from email local part.
    Examples:
      john.smith     -> john, smith
      john_smith     -> john, smith
      john-smith     -> john, smith
      jsmith         -> jsmith, ""
      smithj         -> smithj, ""
    """
    localpart = normalize_text(localpart)

    # Split on obvious separators first
    parts = re.split(r"[._\-+]+", localpart)
    parts = [p for p in parts if p]

    if len(parts) >= 2:
        return parts[0], "", parts[1]

    return localpart, "", ""


def split_name_line(line: str):
    """
    Accepts:
    - First Last
    - First,Last
    - First;Last
    - First|Last
    - First Middle Last
    - email addresses
    Returns: first, middle(s), last, original_email_localpart
    """
    line = normalize_text(line)

    if not line:
        return None, None, None, None

    if is_email(line):
        localpart = line.split("@", 1)[0]
        first, middle, last = split_email_localpart(localpart)
        return first, middle, last, localpart

    for delim in [",", ";", "|"]:
        if delim in line:
            parts = [p.strip() for p in line.split(delim) if p.strip()]
            if len(parts) >= 2:
                first = parts[0]
                last = parts[1]
                middle = " ".join(parts[2:]) if len(parts) > 2 else ""
                return first, middle, last, None

    parts = [p for p in line.split() if p]
    if len(parts) == 1:
        return parts[0], "", "", None
    elif len(parts) == 2:
        return parts[0], "", parts[1], None
    else:
        first = parts[0]
        last = parts[-1]
        middle = " ".join(parts[1:-1])
        return first, middle, last, None


def generate_variations(first: str, middle: str, last: str, original_localpart: str = None):
    results = set()

    first = clean_token(first)
    middle = clean_token(middle)
    last = clean_token(last)
    original_localpart = clean_token(original_localpart) if original_localpart else None

    if not first and not last and not original_localpart:
        return results

    if original_localpart:
        results.add(original_localpart)

    fi = first[0] if first else ""
    mi = middle[0] if middle else ""
    li = last[0] if last else ""

    if first and not last:
        results.update({
            first,
            f"{first}1",
            f"{first}01",
        })
        return {r for r in results if r}

    patterns = {
        f"{first}",
        f"{last}",
        f"{first}.{last}",
        f"{first}_{last}",
        f"{first}-{last}",
        f"{first}{last}",
        f"{fi}{last}",
        f"{first}{li}",
        f"{last}{fi}",
        f"{last}.{first}",
        f"{last}_{first}",
        f"{fi}.{last}",
        f"{first}.{li}",
        f"{fi}{li}",
    }

    if middle:
        patterns.update({
            f"{first}.{middle}.{last}",
            f"{fi}{mi}{last}",
            f"{first}{mi}",
            f"{fi}.{mi}.{last}",
            f"{first}.{mi}.{last}",
        })

    numeric_suffix_patterns = {
        f"{first}1",
        f"{last}1",
        f"{fi}{last}1",
        f"{first}{li}1",
    }

    results.update(patterns)
    results.update(numeric_suffix_patterns)

    return {r for r in results if r and len(r) >= 2}


def extract_lines_from_stdin():
    print("[*] Paste names and/or email addresses below. Press Ctrl-D (Linux/macOS) or Ctrl-Z then Enter (Windows) when done:")
    try:
        return [line.rstrip("\n") for line in __import__("sys").stdin]
    except KeyboardInterrupt:
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Generate username permutations from names and email addresses for Kerbrute."
    )
    parser.add_argument(
        "-i", "--input",
        help="Input file containing names or email addresses."
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output file to save generated usernames."
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Paste names/email addresses directly into stdin."
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=2,
        help="Minimum username length to keep (default: 2)."
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=64,
        help="Maximum username length to keep (default: 64)."
    )

    args = parser.parse_args()

    if not args.input and not args.stdin:
        parser.error("You must supply either --input or --stdin")

    lines = []

    if args.input:
        input_path = Path(args.input)
        if not input_path.is_file():
            print(f"[!] Input file not found: {input_path}")
            return 1

        with input_path.open("r", encoding="utf-8", errors="ignore") as f:
            lines.extend(f.readlines())

    if args.stdin:
        lines.extend(extract_lines_from_stdin())

    usernames = set()
    total_lines = 0
    processed_lines = 0

    for raw_line in lines:
        total_lines += 1
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        first, middle, last, original_localpart = split_name_line(line)
        if first is None:
            continue

        processed_lines += 1
        for username in generate_variations(first, middle, last, original_localpart):
            if args.min_length <= len(username) <= args.max_length:
                usernames.add(username)

    sorted_usernames = sorted(usernames)

    output_path = Path(args.output)
    with output_path.open("w", encoding="utf-8") as f:
        for username in sorted_usernames:
            f.write(username + "\n")

    print(f"[+] Total input lines:   {total_lines}")
    print(f"[+] Parsed entries:      {processed_lines}")
    print(f"[+] Unique usernames:    {len(sorted_usernames)}")
    print(f"[+] Output written to:   {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
