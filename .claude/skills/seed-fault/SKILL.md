---
name: seed-fault
description: Deliberately break the pipeline in one named way, prove the tests and the leakage hook catch it, then fix it and log the evidence. Use for "seed a fault", "break X on purpose", or checking whether a guard actually fires.
allowed-tools: Read, Edit, Bash(git diff*), Bash(git status*), Bash(git commit*), Bash(git checkout*), Bash(make*), Bash(python -m pytest*)
---

# Fault to seed: $ARGUMENTS

0. **Check the starting state.** Run `git status --short` and `make test`.
   If the tree is dirty or any test is red, stop and say so. A fault
   seeded on top of a red suite proves nothing.

1. **Make exactly one change** that introduces the fault in
   "$ARGUMENTS". Use Edit, not Bash, so the PostToolUse hook runs. Show
   `git diff`.

2. **Run `make test`** and keep the full output. Also note whether the
   hook fired, and what it printed if it did (stderr, exit 2).

3. **If nothing went red, that is the finding.** Do not fix the fault
   yet. Name the missing check, write a test for it in the file the hook
   runs (`tests/test_leakage.py`), and run `make test` again to show it
   is now red.

4. **Commit the broken state**:
   `git commit -am "Seeded fault: $ARGUMENTS (<test that went red | NOT caught>)"`.

5. **Fix it** with the smallest edit, run `make test` until it is green,
   and commit with the number of agent turns the fix took in the
   message.

6. **Append to `docs/SEEDED_FAULTS.md`** under a heading for this fault:
   the diff, the red `make test` output and the hook stderr, pasted
   verbatim in ```text blocks, plus the turn count. Paste output, never
   a description of it.

Never seed a fault in `data/raw/`. Rehearse that one on a copy, because
the SHA-256 guard in `src.ingest` is the check under test.
