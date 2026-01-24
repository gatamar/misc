#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

DATE_RE = re.compile(r"^\d{4}_\d{2}_\d{2}\.md$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def merge_text(old_text: str, new_text: str, separator: str) -> str:
    if not old_text:
        return new_text
    if not new_text:
        return old_text
    return old_text.rstrip() + separator + new_text.lstrip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge Logseq journal folders (YYYY_MM_DD.md)."
    )
    parser.add_argument("old_dir", help="Existing journal folder")
    parser.add_argument("new_dir", help="New journal folder to merge in")
    parser.add_argument(
        "--out",
        dest="out_dir",
        default=None,
        help="Output folder. Default: in-place merge into old_dir",
    )
    parser.add_argument(
        "--separator",
        default="\n\n",
        help="String inserted between old and new content when both exist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show actions without writing files",
    )
    args = parser.parse_args()

    old_dir = Path(args.old_dir)
    new_dir = Path(args.new_dir)
    out_dir = Path(args.out_dir) if args.out_dir else old_dir

    if not old_dir.is_dir() or not new_dir.is_dir():
        raise SystemExit("Both old_dir and new_dir must be directories")

    old_files = {p.name: p for p in old_dir.iterdir() if p.is_file() and DATE_RE.match(p.name)}
    new_files = {p.name: p for p in new_dir.iterdir() if p.is_file() and DATE_RE.match(p.name)}

    all_names = sorted(set(old_files) | set(new_files))

    actions = []
    for name in all_names:
        old_path = old_files.get(name)
        new_path = new_files.get(name)
        out_path = out_dir / name

        if old_path and new_path:
            old_text = read_text(old_path)
            new_text = read_text(new_path)
            merged = merge_text(old_text, new_text, args.separator)
            actions.append(f"merge  {name}")
            if not args.dry_run:
                write_text(out_path, merged)
        elif old_path:
            actions.append(f"keep   {name}")
            if not args.dry_run:
                write_text(out_path, read_text(old_path))
        else:
            actions.append(f"add    {name}")
            if not args.dry_run:
                write_text(out_path, read_text(new_path))

    for line in actions:
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
