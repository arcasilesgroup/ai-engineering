#!/usr/bin/env bash
# quickstart-video.sh — deterministic VHS + ffmpeg pipeline for .github/assets/quickstart.mp4.
#
# Records the real local `ai-eng` CLI via quickstart.tape in a throwaway repository, renders the
# 1920x1080 brand cards, burned-in captions, and non-colour-only highlight overlays from
# brand/tokens.json, composites them with ffmpeg into a silent 16:9 H.264 MP4, and updates
# .github/assets/tapes/quickstart-facts.json so the README poster and tests stay pinned to the
# exact numbers from this recording.
#
# Usage:
#   bash .github/assets/tapes/quickstart-video.sh
#   bash .github/assets/tapes/quickstart-video.sh --from-raw <raw.mp4> <raw.ascii>

set -euo pipefail

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
REPO_ROOT=$(CDPATH='' cd -- "$SCRIPT_DIR/../../.." && pwd -P)
TAPE="$SCRIPT_DIR/quickstart.tape"
OUT_MP4="$REPO_ROOT/.github/assets/quickstart.mp4"
FACTS_JSON="$SCRIPT_DIR/quickstart-facts.json"

for tool in ffmpeg ffprobe bun; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "quickstart-video: missing required tool: $tool" >&2
    exit 1
  fi
done

WORK=$(mktemp -d "${TMPDIR:-/tmp}/aie-quickstart-video.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

if [ "${1:-}" = "--from-raw" ]; then
  if [ "$#" -ne 3 ]; then
    echo "usage: $0 --from-raw <raw.mp4> <raw.ascii>" >&2
    exit 1
  fi
  RAW_MP4="$2"
  RAW_ASCII="$3"
else
  for tool in vhs ai-eng; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      echo "quickstart-video: missing required tool: $tool" >&2
      exit 1
    fi
  done
  cp "$TAPE" "$WORK/quickstart.tape"
  ( cd "$WORK" && vhs quickstart.tape )
  RAW_MP4="$WORK/raw.mp4"
  RAW_ASCII="$WORK/raw.ascii"
fi

OVERLAY_DIR="$WORK/overlays"
bun "$REPO_ROOT/scripts/quickstart-video.ts" "$RAW_MP4" "$RAW_ASCII" "$OVERLAY_DIR" "$FACTS_JSON"

# Read the deterministic input arguments generated beside the filtergraph.
FFMPEG_INPUTS=()
while IFS= read -r arg; do
  FFMPEG_INPUTS+=("$arg")
done < "$OVERLAY_DIR/inputs.args"

# Deterministic silent 16:9 H.264 MP4 tuned for crisp terminal text and instant streaming.
FILTERGRAPH=$(cat "$OVERLAY_DIR/filtergraph.txt")
ffmpeg -y -loglevel error \
  "${FFMPEG_INPUTS[@]}" \
  -filter_complex "$FILTERGRAPH" \
  -map "[vout]" \
  -an \
  -c:v libx264 \
  -preset slow \
  -crf 21 \
  -tune stillimage \
  -pix_fmt yuv420p \
  -movflags +faststart \
  -map_metadata -1 \
  -fflags +bitexact \
  "$OUT_MP4"

# Record the exact muxed duration back into facts JSON so poster & tests match the MP4 to 0.1 s.
ACTUAL_DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUT_MP4")
bun -e '
import { readFileSync, writeFileSync } from "node:fs";
const [factsPath, rawDur] = process.argv.slice(1);
const facts = JSON.parse(readFileSync(factsPath!, "utf8"));
facts.durationSeconds = Number(Number(rawDur).toFixed(1));
writeFileSync(factsPath!, `${JSON.stringify(facts, null, 2)}\n`, "utf8");
' "$FACTS_JSON" "$ACTUAL_DURATION"

SIZE_BYTES=$(wc -c < "$OUT_MP4" | tr -d ' ')
echo "ok  .github/assets/quickstart.mp4 (${SIZE_BYTES} bytes, ${ACTUAL_DURATION}s)"

bun "$REPO_ROOT/scripts/readme-assets.ts" quickstart-poster
