#!/usr/bin/env bash
set -euo pipefail

# Business wake phrase. Exact matching is performed by the Windows ASR client.
KEYWORD="小具同学"

CONFIG_CANDIDATES=(
    "/home/bst/SpeechRelease/SpeechReleaseServer/speech_server.json"
    "/home/SpeechRelease/SpeechReleaseServer/speech_server.json"
)
CONFIG_PATH=""
for candidate in "${CONFIG_CANDIDATES[@]}"; do
    if [[ -f "$candidate" ]]; then
        CONFIG_PATH="$candidate"
        break
    fi
done

if [[ -z "$CONFIG_PATH" ]]; then
    echo "ERROR: speech_server.json was not found." >&2
    echo "Checked:" >&2
    printf '  %s\n' "${CONFIG_CANDIDATES[@]}" >&2
    exit 2
fi

echo "Using configuration: $CONFIG_PATH"

BACKUP_PATH="${CONFIG_PATH}.bak.$(date +%Y%m%d_%H%M%S)"
cp -- "$CONFIG_PATH" "$BACKUP_PATH"

python3 - "$CONFIG_PATH" "$KEYWORD" <<'PY'
import json
import os
import sys
import tempfile

path, keyword = sys.argv[1:3]
with open(path, "r", encoding="utf-8-sig") as stream:
    data = json.load(stream)

changed = 0

def replace_keyword(value):
    global changed
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "keyword":
                if child != keyword:
                    value[key] = keyword
                    changed += 1
            else:
                replace_keyword(child)
    elif isinstance(value, list):
        for child in value:
            replace_keyword(child)

replace_keyword(data)
if changed == 0:
    # Distinguish an already-correct file from a file with no keyword setting.
    def contains_keyword(value):
        if isinstance(value, dict):
            return "keyword" in value or any(contains_keyword(child) for child in value.values())
        if isinstance(value, list):
            return any(contains_keyword(child) for child in value)
        return False
    if not contains_keyword(data):
        raise SystemExit('ERROR: JSON does not contain a "keyword" field')

directory = os.path.dirname(path)
fd, temporary_path = tempfile.mkstemp(prefix=".speech_server.", suffix=".json", dir=directory)
try:
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary_path, path)
finally:
    if os.path.exists(temporary_path):
        os.unlink(temporary_path)

print(f'keyword="{keyword}"; updated fields={changed}')
PY

echo "Configuration backup: $BACKUP_PATH"
echo "Keyword configuration completed. The speech service was not started."
