#!/bin/bash
# Bring every DF-related repo to its most current upstream version.
# Fast-forward only. Never discards local work; reports and skips instead.
BASE="/Users/nathanielcannon/Claude/GitRepos"
VENDOR="/Users/nathanielcannon/Claude/Projects/DwarfCron/repos"

REPOS="\
$BASE/dfhack-latest $BASE/dfhack-53.10-r1 $BASE/dfhack-0.50.13-r1.1 $BASE/dfhack-0.47.05-r8 \
$BASE/df-structures $BASE/df_misc $BASE/dfhack-build-env \
$BASE/dfhack-client-python $BASE/dfhack-remote $BASE/dfhack-remote-alexchandel \
$BASE/DFHackRPC $BASE/dfhack-mcp \
$BASE/myDFHackScripts $BASE/eld-dfhack-scripts $BASE/dfhack-scripts-robob27 $BASE/dfhack-commands \
$BASE/DF-Modloader $BASE/ModHearth $BASE/Nexus-Mod-Manager $BASE/PyDwarf $BASE/DF-BAMM \
$BASE/python-lnp $BASE/DwarfGenManager $BASE/dfraw_parser \
$BASE/LegendsViewer-Next $BASE/LegendsViewer $BASE/LegendsBrowser2 $BASE/LegendsBrowser \
$BASE/weblegends $BASE/df-narrator $BASE/df-sites-analyzer $BASE/Dwarfipedia \
$BASE/df-ai $BASE/DwarvenSurveyor $BASE/DwarfFortressLogger \
$BASE/dwarf-eye $BASE/armok-vision $BASE/multi-dwarf $BASE/dwarf-with-friends \
$BASE/df-smooth-movement \
$BASE/mac-dwarf $BASE/dwarf-fortress-macos $BASE/Whisky \
$VENDOR/dfhack $VENDOR/Dwarf-Therapist \
/Users/nathanielcannon/Claude/Projects/seasonal-wildlife"

printf "%-28s %-10s %-10s %s\n" "REPO" "BEFORE" "AFTER" "RESULT"
for r in $REPOS; do
  name=$(basename "$r")
  [ -d "$r/.git" ] || { printf "%-28s %-10s %-10s %s\n" "$name" "-" "-" "NOT-A-GIT-REPO"; continue; }

  before=$(git -C "$r" rev-parse --short HEAD 2>/dev/null)
  dirty=""
  [ -n "$(git -C "$r" status --porcelain 2>/dev/null)" ] && dirty="DIRTY "

  if ! git -C "$r" fetch --all --tags --quiet 2>/dev/null; then
    printf "%-28s %-10s %-10s %s\n" "$name" "$before" "$before" "${dirty}FETCH-FAILED"
    continue
  fi

  branch=$(git -C "$r" rev-parse --abbrev-ref HEAD 2>/dev/null)
  if [ "$branch" = "HEAD" ]; then
    printf "%-28s %-10s %-10s %s\n" "$name" "$before" "$before" "${dirty}DETACHED-fetched-only"
    continue
  fi

  upstream=$(git -C "$r" rev-parse --abbrev-ref "@{u}" 2>/dev/null)
  if [ -z "$upstream" ]; then
    printf "%-28s %-10s %-10s %s\n" "$name" "$before" "$before" "${dirty}NO-UPSTREAM-fetched-only"
    continue
  fi

  if [ -n "$dirty" ]; then
    behind=$(git -C "$r" rev-list --count "HEAD..$upstream" 2>/dev/null)
    printf "%-28s %-10s %-10s %s\n" "$name" "$before" "$before" "DIRTY-skipped (${behind} behind)"
    continue
  fi

  if git -C "$r" merge --ff-only "$upstream" --quiet 2>/dev/null; then
    after=$(git -C "$r" rev-parse --short HEAD)
    if [ "$before" = "$after" ]; then res="already-current"; else res="UPDATED"; fi
    printf "%-28s %-10s %-10s %s\n" "$name" "$before" "$after" "$res"
  else
    behind=$(git -C "$r" rev-list --count "HEAD..$upstream" 2>/dev/null)
    printf "%-28s %-10s %-10s %s\n" "$name" "$before" "$before" "NOT-FF (${behind} behind)"
  fi
done
