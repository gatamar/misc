#!/usr/bin/env python3
import argparse
import re
import shutil
import sys
from pathlib import Path

DATE_RE = re.compile(r"^\d{4}_\d{2}_\d{2}\.md$")
GRAPH_SUBDIRS = ("journals", "pages", "assets")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_file(source: Path, destination: Path) -> None:
    if destination.exists() and source.resolve() == destination.resolve():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def merge_text(old_text: str, new_text: str, separator: str) -> str:
    if not old_text:
        return new_text
    if not new_text:
        return old_text
    return old_text.rstrip() + separator + new_text.lstrip()


def find_existing_match(old_text: str, new_text: str):
    if not old_text or not new_text:
        return None

    index = old_text.find(new_text)
    if index != -1:
        return new_text, index

    appended_text = new_text.lstrip()
    if appended_text != new_text and appended_text:
        index = old_text.find(appended_text)
        if index != -1:
            return appended_text, index

    return None


def format_duplicate_warning(label: str, name: str, match_text: str, index: int) -> str:
    newline = "" if match_text.endswith("\n") else "\n"
    return (
        f"WARNING: {label}/{name}: new content already exists in the old file "
        f"at character offset {index}; not appending duplicate.\n"
        "Exact match follows:\n"
        "----- BEGIN EXACT MATCH -----\n"
        f"{match_text}{newline}"
        "----- END EXACT MATCH -----"
    )


def collect_direct_files(directory: Path, matcher) -> dict[str, Path]:
    if not directory.is_dir():
        return {}
    return {
        p.name: p
        for p in directory.iterdir()
        if p.is_file() and matcher(p.name)
    }


def collect_recursive_files(directory: Path) -> dict[Path, Path]:
    if not directory.is_dir():
        return {}
    return {
        p.relative_to(directory): p
        for p in directory.rglob("*")
        if p.is_file()
    }


def collect_assets_by_name(directory: Path) -> dict[str, list[Path]]:
    assets_by_name: dict[str, list[Path]] = {}
    for path in collect_recursive_files(directory).values():
        assets_by_name.setdefault(path.name.casefold(), []).append(path)
    return assets_by_name


def has_graph_subdirs(directory: Path) -> bool:
    return any((directory / subdir).is_dir() for subdir in GRAPH_SUBDIRS)


def format_asset_conflict_error(
    conflicts: dict[str, tuple[list[Path], list[Path]]],
    old_assets_dir: Path,
    new_assets_dir: Path,
) -> str:
    lines = [
        "Asset filename conflict: refusing to merge assets because "
        f"{len(conflicts)} case-insensitive name(s) exist in both asset folders.",
        "",
        f"Old assets folder: {old_assets_dir}",
        f"New assets folder: {new_assets_dir}",
        "",
        "Rename or remove one side of each conflicting asset before re-running.",
        "Conflicts:",
    ]

    for name in sorted(conflicts):
        old_paths, new_paths = conflicts[name]
        lines.append(f"- {name}")
        lines.append("  old:")
        lines.extend(f"    {path}" for path in sorted(old_paths))
        lines.append("  new:")
        lines.extend(f"    {path}" for path in sorted(new_paths))

    return "\n".join(lines)


def abort_on_asset_conflicts(old_assets_dir: Path, new_assets_dir: Path) -> None:
    old_assets = collect_assets_by_name(old_assets_dir)
    new_assets = collect_assets_by_name(new_assets_dir)
    conflicts = {
        name: (old_assets[name], new_assets[name])
        for name in old_assets.keys() & new_assets.keys()
    }
    if conflicts:
        raise SystemExit(
            format_asset_conflict_error(conflicts, old_assets_dir, new_assets_dir)
        )


def merge_text_folder(
    old_dir: Path,
    new_dir: Path,
    out_dir: Path,
    label: str,
    matcher,
    separator: str,
    dry_run: bool,
) -> list[str]:
    old_files = collect_direct_files(old_dir, matcher)
    new_files = collect_direct_files(new_dir, matcher)

    actions = []
    for name in sorted(set(old_files) | set(new_files)):
        old_path = old_files.get(name)
        new_path = new_files.get(name)
        out_path = out_dir / name

        if old_path and new_path:
            old_text = read_text(old_path)
            new_text = read_text(new_path)
            existing_match = find_existing_match(old_text, new_text)

            if existing_match:
                match_text, index = existing_match
                actions.append(f"skip   {label}/{name}")
                print(
                    format_duplicate_warning(label, name, match_text, index),
                    file=sys.stderr,
                )
                if not dry_run and old_path.resolve() != out_path.resolve():
                    write_text(out_path, old_text)
            else:
                merged = merge_text(old_text, new_text, separator)
                actions.append(f"merge  {label}/{name}")
                if not dry_run:
                    write_text(out_path, merged)
        elif old_path:
            actions.append(f"keep   {label}/{name}")
            if not dry_run:
                write_text(out_path, read_text(old_path))
        else:
            actions.append(f"add    {label}/{name}")
            if not dry_run:
                write_text(out_path, read_text(new_path))

    return actions


def merge_assets_folder(
    old_dir: Path,
    new_dir: Path,
    out_dir: Path,
    dry_run: bool,
) -> list[str]:
    old_files = collect_recursive_files(old_dir)
    new_files = collect_recursive_files(new_dir)

    actions = []
    for relative_path in sorted(set(old_files) | set(new_files)):
        old_path = old_files.get(relative_path)
        new_path = new_files.get(relative_path)
        out_path = out_dir / relative_path
        display_path = relative_path.as_posix()

        if old_path:
            actions.append(f"keep   assets/{display_path}")
            if not dry_run:
                copy_file(old_path, out_path)
        else:
            actions.append(f"add    assets/{display_path}")
            if not dry_run:
                copy_file(new_path, out_path)

    return actions


def merge_journal_folder(
    old_dir: Path,
    new_dir: Path,
    out_dir: Path,
    separator: str,
    dry_run: bool,
) -> list[str]:
    return merge_text_folder(
        old_dir=old_dir,
        new_dir=new_dir,
        out_dir=out_dir,
        label="journals",
        matcher=lambda name: bool(DATE_RE.match(name)),
        separator=separator,
        dry_run=dry_run,
    )


def merge_graph(
    old_root: Path,
    new_root: Path,
    out_root: Path,
    separator: str,
    dry_run: bool,
) -> list[str]:
    old_assets_dir = old_root / "assets"
    new_assets_dir = new_root / "assets"

    abort_on_asset_conflicts(old_assets_dir, new_assets_dir)

    actions = []
    actions.extend(
        merge_journal_folder(
            old_root / "journals",
            new_root / "journals",
            out_root / "journals",
            separator,
            dry_run,
        )
    )
    actions.extend(
        merge_text_folder(
            old_root / "pages",
            new_root / "pages",
            out_root / "pages",
            "pages",
            lambda name: name.endswith(".md"),
            separator,
            dry_run,
        )
    )
    actions.extend(
        merge_assets_folder(
            old_assets_dir,
            new_assets_dir,
            out_root / "assets",
            dry_run,
        )
    )
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge Logseq graph folders."
    )
    parser.add_argument(
        "old_dir",
        help="Existing Logseq graph root, or an existing journal folder",
    )
    parser.add_argument(
        "new_dir",
        help="New Logseq graph root to merge in, or a new journal folder",
    )
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

    if has_graph_subdirs(old_dir) or has_graph_subdirs(new_dir):
        actions = merge_graph(
            old_root=old_dir,
            new_root=new_dir,
            out_root=out_dir,
            separator=args.separator,
            dry_run=args.dry_run,
        )
    else:
        actions = merge_journal_folder(
            old_dir=old_dir,
            new_dir=new_dir,
            out_dir=out_dir,
            separator=args.separator,
            dry_run=args.dry_run,
        )

    for line in actions:
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
