#!/usr/bin/env bash
# Auto-sync the repo at session start.
#
# Strategija: git je kanonska istina. Korisnik radi sa više kompjutera i uvijek
# publishuje najnoviju verziju na origin, pa kad počne sesiju na bilo kojoj
# mašini želi:
#   1. fetch origin
#   2. snimi sve lokalno nepublishovano u "auto-rescue" stash (safety net)
#   3. hard reset radnog direktorijuma na origin/<branch>
#
# Stash NIKAD ne pop-ujemo automatski. Lokalne izmjene se mogu vratiti preko
# `git stash list` → `git stash apply stash@{N}` ako se user predomisli.
#
# .claude/worktrees/ je u .gitignore pa worktree-ovi ostaju netaknuti (nisu
# uključeni u stash -u jer su ignored).

set -u

REPO="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$REPO" 2>/dev/null || {
  jq -n --arg msg "sync hook: cannot cd to $REPO" \
    '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$msg}}'
  exit 0
}

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  exit 0
fi

OUT="=== Auto git sync (SessionStart) ==="$'\n'
OUT+="Strategija: origin je kanon → lokalne nepublishovane izmjene se snimaju u stash i radni direktorijum se resetuje na origin."$'\n\n'

# ── 1. Fetch ──────────────────────────────────────────────────────────────
if FETCH_ERR=$(git fetch origin 2>&1); then
  OUT+="✓ git fetch origin"$'\n'
else
  OUT+="✗ git fetch origin FAILED:"$'\n'"$FETCH_ERR"$'\n'
  OUT+="!! Nastavljam bez sync-a — provjeri mrežu/SSH ključ."$'\n'
  HEAD=$(git rev-parse HEAD 2>/dev/null || echo "?")
  OUT+=$'\n'"HEAD (bez sync-a): $HEAD"$'\n'
  jq -n --arg ctx "$OUT" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
  exit 0
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)
UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || echo "origin/main")

# ── 2. Resolve unresolved merge konflikti (UU stanje iz prethodne sesije) ──
# Ovo je samo da `git stash push` ne padne — sadržaj će biti odbačen reset-om.
UNMERGED=$(git ls-files -u | awk '{print $4}' | sort -u)
if [ -n "$UNMERGED" ]; then
  COUNT=$(echo "$UNMERGED" | grep -c '.')
  OUT+="⚠ $COUNT unresolved konflikt(a) — auto-resolvam (--ours, sadržaj će biti reset-ovan ionako):"$'\n'
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    git checkout --ours -- "$f" 2>/dev/null && git add -- "$f" 2>/dev/null
    OUT+="  • $f"$'\n'
  done <<< "$UNMERGED"
fi

# ── 3. Snimi lokalno stanje u rescue stash (safety net) ───────────────────
STAMP=$(date +%Y-%m-%d_%H:%M:%S)
DIRTY=0
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  DIRTY=1
fi

if [ "$DIRTY" -eq 1 ]; then
  if git stash push -u -m "auto-rescue session-start $STAMP" >/dev/null 2>&1; then
    OUT+="✓ Lokalne izmjene snimljene → \"auto-rescue session-start $STAMP\""$'\n'
    OUT+="  Vraćanje (ako zatreba): git stash list  →  git stash apply stash@{0}"$'\n'
  else
    OUT+="⚠ Stash nije uspio — lokalne izmjene će svejedno biti odbačene reset-om"$'\n'
  fi
else
  OUT+="ℹ Radni direktorijum čist — nema šta da se snimi"$'\n'
fi

# ── 4. Hard reset ka upstream-u ───────────────────────────────────────────
if RESET_OUT=$(git reset --hard "$UPSTREAM" 2>&1); then
  OUT+="✓ Reset hard → $UPSTREAM"$'\n'
  OUT+="  $(echo "$RESET_OUT" | tail -1)"$'\n'
else
  OUT+="✗ git reset --hard FAILED:"$'\n'"$RESET_OUT"$'\n'
fi

# ── 5. Pregled finalnog stanja ────────────────────────────────────────────
HEAD=$(git rev-parse HEAD)
SHORT=$(git rev-parse --short HEAD)
STATUS=$(git status --short)
OUT+=$'\n'"Branch: $BRANCH"$'\n'
OUT+="HEAD:   $SHORT ($HEAD)"$'\n'
if [ -n "$STATUS" ]; then
  OUT+="Working tree (samo .gitignore-ovani / worktrees):"$'\n'"$STATUS"$'\n'
else
  OUT+="Working tree: clean (= $UPSTREAM)"$'\n'
fi

jq -n --arg ctx "$OUT" \
  '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
