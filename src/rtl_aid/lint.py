import re
import subprocess
import sys
import os
import argparse
import shutil
from . import __version__


LINT_RULES = {
    "SENSINCOMPLETE": "Signal(s) read but missing from sensitivity list in always @(...) block",
    "GENUNNAMED": "generate block contains an unlabeled 'begin' (missing ': label')",
}


def _get_verilator_version():
    try:
        out = subprocess.check_output(["verilator", "--version"], text=True)
        return out.strip().splitlines()[0]
    except Exception:
        return None


def _check_verilator():
    if not shutil.which("verilator"):
        print(
            "Error: verilator is not installed or not in PATH.\n"
            "\n"
            "Install it:\n"
            "  Debian / Ubuntu:  sudo apt install verilator\n"
            "  macOS:            brew install verilator\n"
            "  From source:      https://verilator.org/guide/latest/install.html\n"
            "\n"
            "Note: verilator is a system tool and cannot be installed via pip.",
            file=sys.stderr,
        )
        sys.exit(1)


def _run_lint(filepath, include_dirs):
    cmd = ["verilator", "--lint-only", "-Wall"]
    for d in include_dirs:
        # Must be attached (-I<dir>), not space-separated: on Verilator 5.048
        # `-I <dir>` is parsed as a bare positional module-search request and
        # hard-errors with "Cannot find file containing module: '<dir>'".
        cmd.append(f"-I{d}")
    cmd.append(filepath)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout + result.stderr, cmd


def parse_lint_output(output, filepath):
    """Return {line_num: (warning_id, message)} for warnings/errors in
    filepath only.

    warning_id is the part after 'Warning-' (e.g. 'WIDTHEXPAND'), or '' for
    a bare %Error with no dashed category. Preserving it lets an agent cite
    a stable rule ID when justifying a suppression, instead of only having
    free-text that can reword between verilator versions.

    Only the first issue per line is kept — multiple warnings on the same
    line would produce unreadable inline comments. Verilator continuation
    lines (context arrows, notes) are skipped; only lines starting with
    '%Warning' or '%Error' are matched.
    """
    issues = {}
    target_base = os.path.basename(filepath)
    target_abs = os.path.abspath(filepath)

    # Format: %Warning-TYPE: path:line:col: message
    #         %Error: path:line:col: message
    pattern = re.compile(r"^%(Warning[^:]*|Error[^:]*): (.+?):(\d+):\d+: (.+)$")
    for line in output.splitlines():
        m = pattern.match(line)
        if not m:
            continue
        kind = m.group(1)
        warn_file = m.group(2)
        line_num = int(m.group(3))
        message = m.group(4).strip()
        warning_id = kind.split("-", 1)[1] if "-" in kind else ""

        if (os.path.basename(warn_file) == target_base
                or os.path.abspath(warn_file) == target_abs):
            if line_num not in issues:
                issues[line_num] = (warning_id, message)

    return issues


# ===== CUSTOM CHECKS (beyond verilator -Wall) =====
# These checks catch issues that verilator's -Wall misses.
# Each check_*() function returns {line_num: (rule_id, message)}.
# When adding a new check:
#   1. Add function check_<rulename>()
#   2. Add entry to LINT_RULES dict at top
#   3. Call it in main() custom checks section
#   4. Add tests to tests/lint/

def _strip_comments(text):
    """Blank out comment content while preserving line numbers, so English
    words like 'generate' or 'begin' inside a // comment can't be mistaken
    for source keywords by the custom checks below."""
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return text


_ALWAYS_SENS_RE = re.compile(r"always\s*@\s*\(([^)]*)\)")
_IDENT_RE = re.compile(r"\b[A-Za-z_]\w*\b")
_ASSIGN_RHS_RE = re.compile(r"(?:<=|(?<![=!<>])=(?!=))\s*([^;]+);")
_COND_RE = re.compile(r"\b(?:if|case)\s*\(([^)]*)\)")
_SENS_KEYWORDS = {"begin", "end", "if", "else", "case", "endcase", "default"}


def _find_always_block(text, start):
    """Return the text of the block following an always(...) header: a
    begin/end block if present, otherwise a single statement up to ';'."""
    rest = text[start:]
    begin_match = re.match(r"\s*begin\b", rest)
    if not begin_match:
        end = rest.find(";")
        return rest[: end + 1] if end != -1 else rest

    depth = 1
    pos = begin_match.end()
    for kw in re.finditer(r"\bbegin\b|\bend\b", rest[pos:]):
        depth += 1 if kw.group(0) == "begin" else -1
        if depth == 0:
            return rest[: pos + kw.end()]
    return rest


def check_sensitivity_completeness(text):
    """Flag `always @(sig, ...)` blocks (explicit signal list — not `@*` and
    not clocked with posedge/negedge) that read a signal missing from their
    own sensitivity list. Verilator's -Wall does not catch this.
    """
    issues = {}
    text = _strip_comments(text)
    for m in _ALWAYS_SENS_RE.finditer(text):
        sens_text = m.group(1).strip()
        if not sens_text or sens_text == "*" or re.search(r"\b(posedge|negedge)\b", sens_text):
            continue

        sens_signals = {s.strip() for s in sens_text.split(",") if s.strip()}
        block = _find_always_block(text, m.end())

        read = set()
        for cond in _COND_RE.findall(block):
            read.update(_IDENT_RE.findall(cond))
        for rhs in _ASSIGN_RHS_RE.findall(block):
            read.update(_IDENT_RE.findall(rhs))
        read -= _SENS_KEYWORDS

        missing = sorted(read - sens_signals)
        if missing:
            line_num = text[: m.start()].count("\n") + 1
            issues[line_num] = (
                "SENSINCOMPLETE",
                f"Signal(s) {', '.join(missing)} read but missing from sensitivity list",
            )
    return issues


def check_unlabeled_generate(text):
    """Flag `generate` blocks containing a `begin` with no `: label`.
    Verilator's -Wall does not catch this."""
    issues = {}
    text = _strip_comments(text)
    for m in re.finditer(r"\bgenerate\b(.*?)\bendgenerate\b", text, flags=re.S):
        block = m.group(1)
        block_start = m.start(1)
        for bm in re.finditer(r"\bbegin\b(\s*:\s*\w+)?", block):
            if not bm.group(1):
                line_num = text[: block_start + bm.start()].count("\n") + 1
                issues[line_num] = (
                    "GENUNNAMED",
                    "generate block contains an unlabeled 'begin' (missing ': label')",
                )
    return issues


def tag_file(filepath, issues, lint_cmd):
    """Tag warned lines inline and add lint/tb-test header lines.

    Idempotent: re-running replaces existing /* Check: */ tags and
    skips header lines that are already present.
    """
    with open(filepath, "r") as f:
        lines = f.readlines()

    # Tag each warned line with a trailing /* Check: ... */ comment (or
    # /* Check[ID]: ... */ when a stable warning ID is available).
    # Verilator line numbers are 1-based; Python list is 0-based.
    # Guard against line numbers that fall outside the file — this can
    # happen when a warning originates inside a macro expansion.
    for line_num, (warning_id, message) in sorted(issues.items()):
        idx = line_num - 1
        if idx < 0 or idx >= len(lines):
            continue
        line = lines[idx].rstrip("\n")
        line = re.sub(r"\s*/\* Check(\[[^\]]*\])?:.*?\*/", "", line).rstrip()
        tag = f"Check[{warning_id}]" if warning_id else "Check"
        lines[idx] = f"{line}  /* {tag}: {message} */\n"

    # Insert lint/tb-test headers after the leading comment block (copyright
    # headers, file-level comments, blank lines at the top).
    insert_idx = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("//") or s.startswith("/*") or s.startswith("*") or s == "":
            insert_idx = i + 1
        else:
            break

    lint_cmd_str = " ".join(lint_cmd)
    full_content = "".join(lines)
    new_headers = []
    if "// lint-test:" not in full_content:
        new_headers.append(f"// lint-test: {lint_cmd_str}\n")
    else:
        # Update existing lint-test line with the new command
        new_lines = []
        for line in lines[:insert_idx]:
            if line.strip().startswith("// lint-test:"):
                new_lines.append(f"// lint-test: {lint_cmd_str}\n")
            else:
                new_lines.append(line)
        lines = new_lines + lines[insert_idx:]

    if "// tb-test:" not in full_content:
        new_headers.append("// tb-test: tba\n")

    if new_headers:
        lines = lines[:insert_idx] + new_headers + lines[insert_idx:]

    with open(filepath, "w") as f:
        f.writelines(lines)


def main():
    parser = argparse.ArgumentParser(
        prog="rtllint",
        description="Run verilator lint on Verilog files and tag warnings inline"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--list-rules",
        action="store_true",
        help="List all available lint rules and exit"
    )
    parser.add_argument(
        "file",
        nargs="*",
        metavar="FILE",
        help="Verilog/SystemVerilog file(s) to lint"
    )
    parser.add_argument(
        "-I", "--include",
        dest="include_dirs",
        action="append",
        metavar="DIR",
        default=[],
        help="Add include directory (passed to verilator as -I, repeatable)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show issues without modifying any files"
    )
    parser.add_argument(
        "-v",
        action="store_true",
        help="Print full verilator output"
    )
    args = parser.parse_args()

    if args.list_rules:
        print("rtllint custom rules:")
        print()
        for rule_id, description in sorted(LINT_RULES.items()):
            print(f"  {rule_id:<20} {description}")
        print()
        print("For verilator's built-in rule IDs, see:")
        print("  verilator --lint-only -Wall <file>")
        print("or:")
        print("  https://verilator.org/guide/latest/warnings.html")
        sys.exit(0)

    if not args.file:
        parser.error("file: required unless --list-rules is used")

    _check_verilator()

    if args.v:
        print(f"Using {_get_verilator_version()}")

    any_issues = False
    for filepath in args.file:
        if not os.path.isfile(filepath):
            print(f"Error: {filepath}: file not found", file=sys.stderr)
            continue

        output, _ = _run_lint(filepath, args.include_dirs)
        issues = parse_lint_output(output, filepath)

        with open(filepath) as f:
            source = f.read()
        # Custom checks catch things verilator's -Wall doesn't (sensitivity
        # list completeness, unlabeled generate blocks). A verilator finding
        # on the same line always wins.
        for ln, issue in {**check_sensitivity_completeness(source), **check_unlabeled_generate(source)}.items():
            issues.setdefault(ln, issue)

        if args.v and output.strip():
            print(output.strip())

        if not issues:
            print(f"{filepath}: clean")
            continue

        any_issues = True
        # Build rtllint command for tagging
        rtllint_cmd = ["rtllint"]
        for d in args.include_dirs:
            rtllint_cmd.append(f"-I{d}")
        rtllint_cmd.append(filepath)

        if args.dry_run:
            print(f"\n{filepath}: {len(issues)} issue(s) would be tagged:")
            for ln, (warning_id, msg) in sorted(issues.items()):
                tag = f"[{warning_id}] " if warning_id else ""
                print(f"  Line {ln}: {tag}{msg}")
        else:
            tag_file(filepath, issues, rtllint_cmd)
            print(f"{filepath}: tagged {len(issues)} issue(s)")

    sys.exit(1 if any_issues else 0)


if __name__ == "__main__":
    main()
