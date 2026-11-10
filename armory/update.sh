#!/bin/bash
# One-command armory refresh (runs in the Claude desktop Linux VM via device_bash).
#   bash "$HOME/mnt/D2R_Bot_20260314/Codebase/armory_tools/update.sh" [saves_folder]
# Backs up the saves, rescans every character + the shared stash + Chronicle, rebuilds the page,
# and overwrites the root copy "Blizzaga's Armory.html". Never writes to the saves folder.
set -euo pipefail
ROOT="$HOME/mnt/D2R_Bot_20260314"; T="$ROOT/Codebase/armory_tools"
SAVES="${1:-}"
if [ -z "$SAVES" ]; then for d in "$HOME"/mnt/*/; do [ -f "$d/ModernSharedStashSoftCoreV2.d2i" ] && SAVES="${d%/}" && break; done; fi
if [ -z "$SAVES" ]; then echo "NEED_SAVES: connect C:\\Users\\steph\\Saved Games\\Diablo II Resurrected"; exit 2; fi
TS=$(date +%Y%m%d_%H%M%S); B="$ROOT/Codebase/backups/$TS"
mkdir -p "$B"; cp "$SAVES"/*.d2s "$SAVES"/*.d2i "$B"/
W="$HOME/scan"; rm -rf "$W"; mkdir -p "$W/saves"; tar xzf "$T/scanbundle.tgz" -C "$W"
cp "$T"/inv.py "$T"/gen.py "$T"/chron.py "$T"/build.py "$T"/armory.html "$T"/pagedata.json "$W"/
cd "$W"; cp pagedata.json prev.json; chmod +x d2dump
for f in "$B"/*.d2s; do n=$(basename "$f" .d2s); ./d2dump c "$f" > "saves/$n.json"; done
./d2dump s "$B/ModernSharedStashSoftCoreV2.d2i" > saves/stash.json
python3 inv.py . > /dev/null
python3 gen.py > /dev/null
python3 chron.py "$B/ModernSharedStashSoftCoreV2.d2i" > chron.json
python3 build.py
cat pagedata.json > "$T/pagedata.json"
cat armory_built.html > "$T/built_$TS.html"
cat armory_built.html > "$ROOT/.armory_new.html" && mv -f "$ROOT/.armory_new.html" "$ROOT/Blizzaga's Armory.html"
sleep 5  # let Windows settle the rename; staging right after it can see a transient hardlink
echo "OK backup=$TS page=\"$ROOT/Blizzaga's Armory.html\""
