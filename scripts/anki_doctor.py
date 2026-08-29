#!/usr/bin/env python3
"""Bring this machine's Anki setup into line with the repo, and report what it can't fix.

Two laptops share one AnkiWeb collection but *not* the tooling around it: add-ons don't
sync, the venv doesn't sync, the generated vocab caches are gitignored, and a `git pull`
changes nothing in a running Anki. This checks all of that in one pass, fixes what is safe
to fix, and exits non-zero when something needs a person.

    ./scripts/anki_doctor.py              # check and apply safe fixes
    ./scripts/anki_doctor.py --check      # report only, change nothing
    ./scripts/anki_doctor.py --quiet      # print only problems (for a scheduled run)

Stdlib only, and run with *system* python3 on purpose: one of the things it checks is
whether the project venv is intact, so it cannot depend on it. `anki_utils` is imported for
its `call()` alone, which is stdlib (pymorphy3 is loaded lazily, further down that module).

Deliberately not done: `git push`, `git commit`, and any pull that isn't a fast-forward.
Unfinished work on the other laptop is the normal case, not an error, and a scheduled job
is the wrong place to resolve it. Nor does it run the full `autoLimitNow`: mid-day that
recomputes a limit downward from the promoted cards still in the new queue, retiring words
you had left for later. It repairs only decks whose stamp is missing or stale
(`onlyUnstamped`), which is the case a sync from another device creates.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

ADDON_SRC = ROOT / "anki_addon" / "russian_promote"
ADDONS21 = Path.home() / "Library/Application Support/Anki2/addons21"
ADDON_LINK = ADDONS21 / "russian_promote"
VENV_PY = ROOT / ".venv" / "bin" / "python"
CACHES = ("known_lemmas.txt", "known_vocab.tsv")
CACHE_MAX_AGE_H = 24
ADDON_ACTIONS = ("getDeckLimits", "setNewLimitToday", "clearNewLimitToday",
                 "autoLimitNow", "peekQueue", "addonInfo")

OK, FIXED, WARN, FAIL, SKIP = "OK", "FIXED", "WARN", "FAIL", "SKIP"
BAD = (WARN, FAIL)


class Report:
    """Prints as it goes, so a hung check still leaves a usable trail in the log."""

    def __init__(self, quiet, header):
        self.rows, self.quiet, self.header = [], quiet, header
        if not quiet:
            print(header)

    def add(self, check, status, detail):
        self.rows.append((check, status, detail))
        if self.quiet and status in BAD and self.header:
            print(self.header)          # quiet runs stay silent until there is a problem
            self.header = None
        if not self.quiet or status in BAD:
            print(f"  {check:<16} {status:<6} {detail}")

    def problems(self):
        return [r for r in self.rows if r[1] in BAD]


def git(*args, timeout=60):
    """-> (returncode, stdout). Never raises; git being unhappy is a finding, not a crash."""
    try:
        p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as e:
        return 1, str(e)


def anki(action, **params):
    """AnkiConnect call, or None if Anki isn't running."""
    import anki_utils as a
    try:
        return a.call(action, **params)
    except Exception:
        return None


# --- checks -----------------------------------------------------------------

def check_repo(rep, fix):
    if git("rev-parse", "--git-dir")[0] != 0:
        return rep.add("repo", FAIL, f"{ROOT} is not a git repo")

    dirty = bool(git("status", "--porcelain")[1])
    rc, upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if rc != 0:
        return rep.add("repo", WARN, "no upstream branch set (git push -u origin main)")

    # A fetch needs the network and an ssh key; from a scheduled run either may be absent,
    # which is a "couldn't check" rather than a failure.
    rc, out = git("fetch", "--quiet", timeout=90)
    if rc != 0:
        rep.add("repo", WARN, f"could not reach origin ({out.splitlines()[-1][:60] if out else '?'})")
        return

    rc, counts = git("rev-list", "--left-right", "--count", f"HEAD...{upstream}")
    ahead, behind = (counts.split() + ["0", "0"])[:2] if rc == 0 else ("0", "0")
    ahead, behind = int(ahead), int(behind)
    head = git("rev-parse", "--short", "HEAD")[1]

    if behind and dirty:
        return rep.add("repo", WARN, f"{behind} commit(s) behind {upstream} but the tree is "
                                     "dirty — pull by hand")
    if behind and ahead:
        return rep.add("repo", WARN, f"diverged from {upstream} ({ahead} ahead, {behind} "
                                     "behind) — resolve by hand")
    if behind:
        if not fix:
            return rep.add("repo", WARN, f"{behind} commit(s) behind {upstream}")
        rc, out = git("merge", "--ff-only", upstream)
        if rc != 0:
            return rep.add("repo", FAIL, f"fast-forward failed: {out[:80]}")
        return rep.add("repo", FIXED, f"pulled {behind} commit(s) -> {git('rev-parse', '--short', 'HEAD')[1]}")

    extra = []
    if ahead:
        extra.append(f"{ahead} unpushed commit(s)")
    if dirty:
        extra.append("uncommitted changes")
    status = WARN if ahead else OK          # local edits are normal; unpushed ones strand work
    rep.add("repo", status, f"up to date with {upstream} ({head})"
                            + (f"; {', '.join(extra)}" if extra else ""))


def check_addon_link(rep, fix):
    if not ADDON_SRC.is_dir():
        return rep.add("addon link", FAIL, f"missing {ADDON_SRC}")
    if not ADDONS21.is_dir():
        return rep.add("addon link", FAIL, f"no Anki add-ons folder at {ADDONS21}")

    if ADDON_LINK.is_symlink():
        target = ADDON_LINK.resolve()
        if target == ADDON_SRC.resolve():
            return rep.add("addon link", OK, f"-> {ADDON_SRC}")
        return rep.add("addon link", WARN, f"points at {target}, not {ADDON_SRC}")
    if ADDON_LINK.exists():
        # A real directory here is a copy that git will never update — worse than nothing,
        # because it looks installed and silently drifts. Not ours to delete.
        return rep.add("addon link", WARN, f"{ADDON_LINK} is a real directory, not a symlink "
                                           "— remove it, then re-run")
    if not fix:
        return rep.add("addon link", WARN, "not installed")
    try:
        ADDON_LINK.symlink_to(ADDON_SRC)
    except OSError as e:
        return rep.add("addon link", FAIL, f"could not create symlink: {e}")
    rep.add("addon link", FIXED, "symlink created — restart Anki to load it")


def check_addon_running(rep, info, actions):
    if actions is None:
        return rep.add("addon", SKIP, "Anki not running")
    missing = [a for a in ADDON_ACTIONS if a not in actions]
    if missing:
        return rep.add("addon", WARN, f"{len(missing)} action(s) not registered "
                                      f"({', '.join(missing)}) — restart Anki")
    if info is None:
        return rep.add("addon", WARN, "addonInfo missing — running an older copy; restart Anki")
    if info.get("stale"):
        age = (info["currentMtime"] - info["sourceMtime"]) / 60
        return rep.add("addon", WARN, f"source changed {age:.0f} min after Anki loaded it "
                                      "— restart Anki")
    rep.add("addon", OK, f"{len(ADDON_ACTIONS)} actions, loaded "
                         f"{(time.time() - info['loadedAt']) / 3600:.1f}h ago")


def check_toggles(rep, info):
    """Parity: the same add-on file can behave differently if a toggle was edited locally."""
    if info is None:
        return rep.add("toggles", SKIP, "addonInfo unavailable")
    expected = {"AUTO_LIMIT_ON_STARTUP": True, "AUTO_LIMIT_ON_DAY_CHANGE": True,
                "AUTO_LIMIT_ON_SYNC": True, "AUTO_UNTAG_FINISHED": True}
    off = [k for k, v in expected.items() if info["toggles"].get(k) != v]
    if off:
        return rep.add("toggles", WARN, f"non-default: {', '.join(off)}")
    rep.add("toggles", OK, "all defaults")


VENV_PKGS = ("pymorphy3", "pymorphy3-dicts-ru", "PyMuPDF")


def venv_ok():
    if not VENV_PY.exists():
        return False, "missing"
    p = subprocess.run([str(VENV_PY), "-c", "import pymorphy3, pymorphy3_dicts_ru, fitz"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return False, (p.stderr.strip().splitlines() or ["?"])[-1][:70]
    return True, "pymorphy3 + PyMuPDF present"


def check_venv(rep, bootstrap):
    ok, detail = venv_ok()
    if ok:
        return rep.add("venv", OK, detail)
    if not bootstrap:
        # Not part of the default fixes: a scheduled run should not start downloading
        # packages, and on a fresh laptop this is a once-only step.
        return rep.add("venv", WARN, f"{detail} — run scripts/anki_doctor.py --bootstrap")

    rep.add("venv", WARN, f"{detail} — building it now, this takes a minute")
    if not VENV_PY.exists():
        p = subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")],
                           capture_output=True, text=True)
        if p.returncode != 0:
            return rep.add("venv", FAIL, f"venv creation failed: {p.stderr.strip()[:70]}")
    p = subprocess.run([str(ROOT / ".venv" / "bin" / "pip"), "install", "--quiet", *VENV_PKGS],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return rep.add("venv", FAIL, f"pip install failed: {p.stderr.strip()[-70:]}")
    ok, detail = venv_ok()
    rep.add("venv", FIXED if ok else FAIL, detail)


def check_exec_bits(rep):
    """Git records the mode, so a mismatch means this checkout has drifted from the repo."""
    bad = []
    for f in sorted((ROOT / "scripts").glob("*.py")):
        with open(f, "rb") as fh:
            shebang = fh.readline().startswith(b"#!")
        if shebang and not os.access(f, os.X_OK):
            bad.append(f.name)
    if bad:
        return rep.add("exec bits", WARN, f"not executable: {', '.join(bad)} "
                                          f"(chmod +x scripts/*.py)")
    rep.add("exec bits", OK, "all shebanged scripts executable")


def check_limits(rep, fix, running):
    if not running:
        return rep.add("limits", SKIP, "Anki not running")
    cards = anki("findCards", query="tag:promote")
    if not cards:
        return rep.add("limits", OK, "nothing tagged promote")
    decks = sorted({c["deckName"] for c in anki("cardsInfo", cards=cards)})

    def stamps():
        out = {}
        for d in decks:
            lim = anki("getDeckLimits", deck=d) or {}
            val = lim.get("newLimitToday") or {}
            out[d] = (val.get("limit"), val.get("today") == lim.get("schedToday"))
        return out

    before = stamps()
    unstamped = [d for d, (_, valid) in before.items() if not valid]
    if unstamped and fix:
        if anki("autoLimitNow", onlyUnstamped=True) is None:
            return rep.add("limits", WARN, f"{len(unstamped)} deck(s) unstamped and "
                                           "autoLimitNow unavailable")
        after = stamps()
        repaired = [d for d in unstamped if after[d][1]]
        summary = ", ".join(f"{d.split('::')[-1]}={after[d][0]}" for d in decks if after[d][1])
        if repaired:
            return rep.add("limits", FIXED, f"re-stamped {len(repaired)} deck(s): {summary}")
        # Nothing to stamp is the normal end state: the promoted words have been learnt.
        return rep.add("limits", OK, f"{len(unstamped)} deck(s) have no promoted cards left "
                                     "to allow today")
    if unstamped:
        return rep.add("limits", WARN, f"{len(unstamped)} deck(s) with no limit for today: "
                                       f"{', '.join(d.split('::')[-1] for d in unstamped)}")
    rep.add("limits", OK, ", ".join(f"{d.split('::')[-1]}={before[d][0]}" for d in decks))


def check_caches(rep, fix, running):
    stale = [f for f in CACHES
             if not (ROOT / f).exists()
             or (time.time() - (ROOT / f).stat().st_mtime) / 3600 > CACHE_MAX_AGE_H]
    if not stale:
        ages = [(time.time() - (ROOT / f).stat().st_mtime) / 3600 for f in CACHES]
        return rep.add("drill caches", OK, f"fresh ({min(ages):.0f}h old)")
    if not (fix and running and VENV_PY.exists()):
        return rep.add("drill caches", WARN, f"stale/missing: {', '.join(stale)} — run "
                                             "scripts/build_drill_vocab.py")
    p = subprocess.run([str(VENV_PY), str(ROOT / "scripts" / "build_drill_vocab.py")],
                       capture_output=True, text=True)
    if p.returncode != 0:
        last = (p.stderr.strip().splitlines() or ["?"])[-1]
        return rep.add("drill caches", WARN, f"rebuild failed: {last[:70]}")
    rep.add("drill caches", FIXED, "rebuilt from the studied set")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="report only; change nothing")
    ap.add_argument("--quiet", action="store_true", help="print only problems")
    ap.add_argument("--bootstrap", action="store_true",
                    help="also create/repair the project venv (slow; new machine only)")
    args = ap.parse_args()
    fix = not args.check

    rep = Report(args.quiet, f"anki doctor — {time.strftime('%Y-%m-%d %H:%M')}"
                             f"{' (check only)' if args.check else ''}")

    check_repo(rep, fix)
    check_addon_link(rep, fix)

    actions = anki("apiReflect", scopes=["actions"])
    actions = actions["actions"] if actions else None
    info = anki("addonInfo") if actions and "addonInfo" in actions else None
    check_addon_running(rep, info, actions)
    check_toggles(rep, info)
    check_venv(rep, args.bootstrap and fix)
    check_exec_bits(rep)
    check_limits(rep, fix, actions is not None)
    check_caches(rep, fix, actions is not None)

    problems = rep.problems()
    if not args.quiet:
        print(f"=> {len(problems)} problem(s)" if problems else "=> all good")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
