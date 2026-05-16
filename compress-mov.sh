#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/compress-mov.sh [options] input.mov [input2.mov ...]

Compress MOV files with ffmpeg using H.264 video and AAC audio.

Options:
  -o, --output FILE       Output file. Only valid with a single input.
  -d, --output-dir DIR    Directory for compressed files.
  --suffix TEXT           Output suffix before extension. Default: -compressed
  --crf VALUE             H.264 quality, 0-51. Lower is better/larger. Default: 24
  --preset NAME           ffmpeg preset: ultrafast, fast, medium, slow, etc. Default: medium
  --audio-bitrate RATE    AAC audio bitrate. Default: 128k
  --overwrite             Replace an existing output file.
  --dry-run               Print the ffmpeg command without running it.
  -h, --help              Show this help.

Examples:
  scripts/compress-mov.sh detail-page-1.mov
  scripts/compress-mov.sh --crf 28 --preset slow *.mov
  scripts/compress-mov.sh -o demo-small.mov detail-page-1.mov
USAGE
}

die() {
  echo "compress-mov: $*" >&2
  exit 1
}

print_command() {
  local arg
  for arg in "$@"; do
    printf '%q ' "$arg"
  done
  printf '\n'
}

require_number() {
  local name=$1
  local value=$2

  case "$value" in
    ''|*[!0-9]*) die "$name must be a number" ;;
  esac
}

make_output_path() {
  local input=$1
  local dir
  local base
  local name
  local ext

  if [ -n "$output_file" ]; then
    printf '%s\n' "$output_file"
    return
  fi

  dir=$(dirname "$input")
  base=$(basename "$input")
  name=${base%.*}
  ext=${base##*.}

  if [ "$base" = "$ext" ]; then
    ext=mov
  fi

  if [ -n "$output_dir" ]; then
    dir=$output_dir
  fi

  printf '%s/%s%s.%s\n' "$dir" "$name" "$suffix" "$ext"
}

same_path() {
  local left=$1
  local right=$2
  local left_dir
  local right_dir
  local left_abs
  local right_abs

  left_dir=$(dirname "$left")
  right_dir=$(dirname "$right")
  mkdir -p "$right_dir"

  left_abs=$(cd "$left_dir" && pwd -P)/$(basename "$left")
  right_abs=$(cd "$right_dir" && pwd -P)/$(basename "$right")

  [ "$left_abs" = "$right_abs" ]
}

crf=24
preset=medium
audio_bitrate=128k
suffix=-compressed
output_dir=
output_file=
overwrite=0
dry_run=0
inputs=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -o|--output)
      [ "$#" -ge 2 ] || die "$1 requires a value"
      output_file=$2
      shift 2
      ;;
    --output=*)
      output_file=${1#*=}
      shift
      ;;
    -d|--output-dir)
      [ "$#" -ge 2 ] || die "$1 requires a value"
      output_dir=$2
      shift 2
      ;;
    --output-dir=*)
      output_dir=${1#*=}
      shift
      ;;
    --suffix)
      [ "$#" -ge 2 ] || die "$1 requires a value"
      suffix=$2
      shift 2
      ;;
    --suffix=*)
      suffix=${1#*=}
      shift
      ;;
    --crf)
      [ "$#" -ge 2 ] || die "$1 requires a value"
      crf=$2
      shift 2
      ;;
    --crf=*)
      crf=${1#*=}
      shift
      ;;
    --preset)
      [ "$#" -ge 2 ] || die "$1 requires a value"
      preset=$2
      shift 2
      ;;
    --preset=*)
      preset=${1#*=}
      shift
      ;;
    --audio-bitrate)
      [ "$#" -ge 2 ] || die "$1 requires a value"
      audio_bitrate=$2
      shift 2
      ;;
    --audio-bitrate=*)
      audio_bitrate=${1#*=}
      shift
      ;;
    --overwrite)
      overwrite=1
      shift
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    --)
      shift
      while [ "$#" -gt 0 ]; do
        inputs+=("$1")
        shift
      done
      ;;
    -*)
      die "unknown option: $1"
      ;;
    *)
      inputs+=("$1")
      shift
      ;;
  esac
done

[ "${#inputs[@]}" -gt 0 ] || die "at least one input .mov file is required"

if [ -n "$output_file" ] && [ "${#inputs[@]}" -ne 1 ]; then
  die "--output can only be used with a single input"
fi

require_number "--crf" "$crf"
if [ "$crf" -lt 0 ] || [ "$crf" -gt 51 ]; then
  die "--crf must be between 0 and 51"
fi

if [ "$dry_run" -eq 0 ]; then
  command -v ffmpeg >/dev/null 2>&1 || die "ffmpeg is not installed or not on PATH"
fi

for input in "${inputs[@]}"; do
  [ -f "$input" ] || die "input not found: $input"

  case "$input" in
    *.[Mm][Oo][Vv]) ;;
    *) echo "compress-mov: warning: input does not end in .mov: $input" >&2 ;;
  esac

  output=$(make_output_path "$input")
  output_parent=$(dirname "$output")
  mkdir -p "$output_parent"

  if same_path "$input" "$output"; then
    die "output path matches input path: $output"
  fi

  ffmpeg_args=(-hide_banner)
  if [ "$overwrite" -eq 1 ]; then
    ffmpeg_args+=(-y)
  else
    ffmpeg_args+=(-n)
  fi

  ffmpeg_args+=(
    -i "$input"
    -map 0:v:0
    -map '0:a?'
    -map_metadata 0
    -map_chapters 0
    -c:v libx264
    -preset "$preset"
    -crf "$crf"
    -pix_fmt yuv420p
    -tag:v avc1
    -c:a aac
    -b:a "$audio_bitrate"
    -movflags +faststart
    "$output"
  )

  if [ "$dry_run" -eq 1 ]; then
    print_command ffmpeg "${ffmpeg_args[@]}"
  else
    ffmpeg "${ffmpeg_args[@]}"
    echo "Wrote $output"
  fi
done
