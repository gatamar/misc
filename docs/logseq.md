# Logseq Backup Structure

This repository currently contains `merge_logseq_journals.py`, a small utility for
merging selected parts of two Logseq graph backups.

## What an iOS Logseq backup usually contains

A Logseq graph backup is normally a folder with subfolders such as:

- `journals/` - daily journal pages.
- `pages/` - normal graph pages.
- `assets/` - attachments such as images, PDFs, and other files.
- `logseq/` - Logseq configuration, metadata, and graph settings.

The exact backup may contain more folders, depending on the Logseq version,
plugins, sync state, and graph contents.

## What the script knows

`merge_logseq_journals.py` understands these folders in a Logseq graph root:

- `journals/`
- `pages/`
- `assets/`

It does not merge the `logseq/` configuration folder.

## Journals

Journal files are Markdown files directly inside `journals/` named like:

```text
YYYY_MM_DD.md
```

For example, a graph root may contain:

```text
old-backup/journals/2026_05_20.md
new-backup/journals/2026_05_20.md
```

The script identifies journal files with this exact filename pattern:

```text
four digits, underscore, two digits, underscore, two digits, .md
```

Journal examples the script will read:

- `2026_05_20.md`
- `2024_01_03.md`

Journal examples the script will ignore:

- `2026-05-20.md`
- `May 20th, 2026.md`
- `2026_05_20.org`
- folders inside `journals/`

## Pages

Page files are Markdown files directly inside `pages/`.

For every page filename found in either input graph:

- If the page exists in both graphs, the old text is followed by the new text.
- If the text that would be appended already exists exactly in the old page, the
  script logs a warning and does not append it again.
- If the page exists only in the old graph, it is copied as-is.
- If the page exists only in the new graph, it is copied as-is.

The script treats page files as plain UTF-8 text. It does not parse Logseq page
references, block IDs, or properties.

## Assets

Asset files are copied recursively from `assets/`.

Assets are intentionally not merged by content. If the old and new `assets/`
folders both contain an asset with the same filename, the script prints a
detailed conflict error and aborts before writing output. This check is by
case-insensitive filename, even if the files are in different subfolders under
`assets/`.

For example, this is refused:

```text
old-backup/assets/photo.jpeg
new-backup/assets/photo.jpeg
```

## What the script does not know

The script understands only `journals/`, `pages/`, and `assets/`.

It does not parse Logseq syntax, page references, block IDs, properties, or
configuration files. It treats matching journal and page files as plain UTF-8
text.

In a backup shaped like `tmp/iphone`, pass `tmp/iphone` as the graph root. The
script will then look inside `tmp/iphone/journals`, `tmp/iphone/pages`, and
`tmp/iphone/assets`.

## Merge behavior

For every journal or page filename found in either input graph:

- If the file exists in both folders, the old text is followed by the new text.
- If the text that would be appended already exists exactly in the old file, the
  script logs a warning with the exact matching text and does not append it again.
- If the file exists only in the old folder, it is copied as-is.
- If the file exists only in the new folder, it is copied as-is.

By default, output is written back into the old graph root. Use `--out` to
write merged files somewhere else:

```sh
./merge_logseq_journals.py old-backup new-backup --out merged-backup
```

Use `--dry-run` to print the planned actions without writing files:

```sh
./merge_logseq_journals.py old-backup new-backup --dry-run
```

For backwards compatibility, if both inputs are plain journal folders rather
than graph roots, the script still merges them as journal folders only.
