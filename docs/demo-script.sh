#!/usr/bin/env bash
# Version: 2026-09-05-v1
#
# The transcript in docs/DEMO.md, as a runnable script. Use it to record a
# terminal capture, or to check that the documented output still matches
# reality after a change.
#
#   bash docs/demo-script.sh                     # run it
#   asciinema rec demo.cast -c "bash docs/demo-script.sh"   # record it
#
# Run from the repository root. It creates a throwaway project under
# .demo-tmp/ and deletes it on exit.

set -euo pipefail

PROJECT=".demo-tmp/sleep-duration-and-next-day-recall"
PYTHON="${PYTHON:-python}"

cleanup() { rm -rf .demo-tmp; }
trap cleanup EXIT

pause() { sleep "${DEMO_PAUSE:-1}"; }

say() {
    printf '\n\033[1;36m$ %s\033[0m\n' "$*"
    pause
}

run() {
    say "$@"
    "$@" || true
    pause
}

rm -rf .demo-tmp

run "$PYTHON" scripts/quick_start.py --list

run "$PYTHON" scripts/quick_start.py \
    --title "Sleep duration and next-day recall" \
    --discipline psychology \
    --project-dir "$PROJECT"

run "$PYTHON" scripts/discipline_profile.py requirements psychology

# The gate refuses to advance: there is no research question yet.
run "$PYTHON" scripts/autopilot.py advance --project-dir "$PROJECT"

say "cat > $PROJECT/notes/research-question.md"
cat > "$PROJECT/notes/research-question.md" <<'QUESTION'
Question: does a night of restricted sleep reduce next-day free recall of
word lists, relative to a habitual-sleep night, in healthy adults aged 18 to 35?
Population: university students screened for sleep disorders and shift work.
Out of scope: recognition memory, clinical insomnia populations, and any claim
about long-term consolidation beyond 24 hours.
QUESTION
pause

run "$PYTHON" scripts/autopilot.py advance --project-dir "$PROJECT"

# An entry that would render as an unusable APA reference.
say "cat >> $PROJECT/ref.bib"
cat >> "$PROJECT/ref.bib" <<'ENTRY'
@misc{smith2019,
  title = {Sleep and memory},
  year  = {2019}
}
ENTRY
pause

run "$PYTHON" scripts/citation_style.py validate apa7 --bib "$PROJECT/ref.bib"

run "$PYTHON" scripts/export_document.py --input "$PROJECT/main.md" --style apa7

run "$PYTHON" scripts/autopilot.py status --project-dir "$PROJECT"

printf '\n\033[1;32mThe skeleton builds and says nothing. The argument is yours.\033[0m\n'
