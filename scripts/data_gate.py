#!/usr/bin/env python3
"""Data-to-prose gate: re-run the analysis behind a table or figure. 2026-09-05-v1.

The citation gates keep the bibliography honest. Nothing in the workflow did the
same for numbers, and a reported measurement is as easy to invent as a reference.

This gate binds each numeric float in a manuscript to a command that regenerates
its data, re-runs that command, and compares every number printed in the float
against the values the command actually produced. A number in the paper with no
counterpart in the regenerated data is a finding.

Manifest: <project-dir>/notes/data-bindings.json

  {
    "bindings": [
      {
        "label": "tab:verify",
        "command": "python analysis/verify_runs.py --out results/verify.json",
        "produces": "results/verify.json",
        "tolerance": 0.01,
        "ignore": [45]
      }
    ]
  }

  label      \\label{...} of the table or figure in the manuscript (required)
  command    command that regenerates the data; omitted means "do not run"
  produces   JSON or CSV file the command writes (required)
  tolerance  relative tolerance for a match (default 0.005)
  ignore     numbers in the float that are labels, not measurements

JSON is the manifest format because the YAML subset used elsewhere in this skill
does not carry lists of mappings.

Exit codes: 0 all bound floats reconcile; 1 a mismatch, a missing file, or a
failed command; 2 usage error.

Usage:
  python scripts/data_gate.py --project-dir <paper_dir>
  python scripts/data_gate.py --project-dir <paper_dir> --no-run   # compare against existing outputs
  python scripts/data_gate.py --project-dir <paper_dir> --init     # write a manifest skeleton
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paper_utils import now_iso

BANNER = "data_gate 2026-09-05-v1"
MANIFEST_NAME = "data-bindings.json"
DEFAULT_TOLERANCE = 0.005

_LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
_ENV_BEGIN_RE = re.compile(r"\\begin\{([A-Za-z][A-Za-z0-9*]*)\}")
_ENV_END_RE = re.compile(r"\\end\{([A-Za-z][A-Za-z0-9*]*)\}")
_FLOAT_ENVIRONMENTS = frozenset({"table", "table*", "figure", "figure*"})
# Numbers as a reader sees them: 45, 3.14, 1,024, 95.6%, -0.5
_NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
# LaTeX constructs whose digits are layout, not data.
_LAYOUT_RE = re.compile(
    r"\\(?:label|ref|cite[a-zA-Z]*|includegraphics|hspace|vspace|arraystretch|"
    r"scalebox|resizebox|multicolumn|multirow|cline|renewcommand|newcolumntype|"
    r"columnwidth|textwidth|linewidth|footnotesize|scriptsize|small)\b[^\n]*"
)
_MEASURE_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:pt|cm|mm|in|em|ex|\\textwidth|\\columnwidth)")


@dataclass
class Binding:
    label: str
    produces: str
    command: str = ""
    tolerance: float = DEFAULT_TOLERANCE
    ignore: list[float] = field(default_factory=list)


@dataclass
class BindingResult:
    label: str
    status: str  # "PASS" | "FAIL" | "SKIP"
    detail: str
    unmatched: list[float] = field(default_factory=list)
    checked: int = 0


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def find_float_body(tex_text: str, label: str) -> str | None:
    """Return the source of the float environment carrying \\label{label}."""
    lines = tex_text.splitlines()
    stack: list[tuple[str, int]] = []
    for i, line in enumerate(lines):
        for match in _ENV_BEGIN_RE.finditer(line):
            stack.append((match.group(1), i))
        for match in _ENV_END_RE.finditer(line):
            if not stack:
                continue
            name, start = stack.pop()
            if name not in _FLOAT_ENVIRONMENTS:
                continue
            body = "\n".join(lines[start : i + 1])
            if any(found == label for found in _LABEL_RE.findall(body)):
                return body
    return None


def numbers_in_float(body: str) -> list[float]:
    """Numbers a reader would read as data, with layout digits removed."""
    text = _LAYOUT_RE.sub(" ", body)
    text = _MEASURE_RE.sub(" ", text)
    text = re.sub(r"%.*", " ", text)
    values: list[float] = []
    for token in _NUMBER_RE.findall(text):
        try:
            values.append(float(token.replace(",", "")))
        except ValueError:
            continue
    return values


def _walk_json(node, out: list[float]) -> None:
    if isinstance(node, bool):
        return
    if isinstance(node, (int, float)):
        out.append(float(node))
        return
    if isinstance(node, str):
        for token in _NUMBER_RE.findall(node):
            try:
                out.append(float(token.replace(",", "")))
            except ValueError:
                pass
        return
    if isinstance(node, dict):
        for value in node.values():
            _walk_json(value, out)
        return
    if isinstance(node, list):
        for value in node:
            _walk_json(value, out)


def numbers_in_data_file(path: Path) -> list[float]:
    """Every numeric value in a JSON or CSV result file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    values: list[float] = []
    if path.suffix.lower() == ".json":
        try:
            _walk_json(json.loads(text), values)
            return values
        except json.JSONDecodeError:
            pass  # fall through and treat it as text
    if path.suffix.lower() in (".csv", ".tsv"):
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        for row in csv.reader(io.StringIO(text), delimiter=delimiter):
            for cell in row:
                for token in _NUMBER_RE.findall(cell):
                    try:
                        values.append(float(token.replace(",", "")))
                    except ValueError:
                        pass
        return values
    for token in _NUMBER_RE.findall(text):
        try:
            values.append(float(token.replace(",", "")))
        except ValueError:
            pass
    return values


def matches_any(value: float, produced: list[float], tolerance: float) -> bool:
    """A paper number reconciles when some produced value is within tolerance."""
    for candidate in produced:
        if value == candidate:
            return True
        scale = max(abs(value), abs(candidate), 1e-9)
        if abs(value - candidate) / scale <= tolerance:
            return True
    return False


def load_manifest(path: Path) -> list[Binding]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("bindings")
    if not isinstance(raw, list):
        raise ValueError("manifest needs a 'bindings' list")
    bindings: list[Binding] = []
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"binding {i} is not an object")
        label = str(item.get("label", "")).strip()
        produces = str(item.get("produces", "")).strip()
        if not label or not produces:
            raise ValueError(f"binding {i} needs both 'label' and 'produces'")
        bindings.append(
            Binding(
                label=label,
                produces=produces,
                command=str(item.get("command", "")).strip(),
                tolerance=float(item.get("tolerance", DEFAULT_TOLERANCE)),
                ignore=[float(v) for v in item.get("ignore", [])],
            )
        )
    return bindings


def run_command(command: str, cwd: Path, timeout_s: float) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            shlex.split(command),
            cwd=str(cwd),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
        )
    except FileNotFoundError as exc:
        return False, f"command not found: {exc}"
    except subprocess.TimeoutExpired:
        return False, f"command timed out after {timeout_s:.0f}s"
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "").strip().splitlines()
        return False, f"command exited {completed.returncode}: {tail[-1] if tail else 'no output'}"
    return True, "ok"


def check_binding(
    binding: Binding, project_dir: Path, tex_text: str, *, run: bool, timeout_s: float
) -> BindingResult:
    body = find_float_body(tex_text, binding.label)
    if body is None:
        return BindingResult(binding.label, "FAIL", f"no float carries \\label{{{binding.label}}}")

    if run and binding.command:
        ok, detail = run_command(binding.command, project_dir, timeout_s)
        if not ok:
            return BindingResult(binding.label, "FAIL", detail)

    data_path = (project_dir / binding.produces).resolve()
    if not data_path.is_file():
        return BindingResult(binding.label, "FAIL", f"missing output: {binding.produces}")

    produced = numbers_in_data_file(data_path)
    if not produced:
        return BindingResult(binding.label, "FAIL", f"no numbers in {binding.produces}")

    ignored = set(binding.ignore)
    paper_values = [v for v in numbers_in_float(body) if v not in ignored]
    unmatched = [v for v in paper_values if not matches_any(v, produced, binding.tolerance)]

    if unmatched:
        return BindingResult(
            binding.label,
            "FAIL",
            f"{len(unmatched)} of {len(paper_values)} number(s) not in {binding.produces}",
            unmatched=unmatched,
            checked=len(paper_values),
        )
    return BindingResult(
        binding.label,
        "PASS",
        f"{len(paper_values)} number(s) reconcile with {binding.produces}",
        checked=len(paper_values),
    )


def write_report(path: Path, results: list[BindingResult], *, ran: bool) -> None:
    lines = [
        "# Data Gate Report",
        "",
        f"- Created at: {now_iso()}",
        f"- Commands re-run: {'yes' if ran else 'no (--no-run)'}",
        f"- Bindings checked: {len(results)}",
        "",
        "| Float | Verdict | Detail |",
        "|---|---|---|",
    ]
    for result in results:
        lines.append(f"| `{result.label}` | {result.status} | {result.detail} |")
    unmatched = [r for r in results if r.unmatched]
    if unmatched:
        lines += ["", "## Numbers with no counterpart in the regenerated data", ""]
        for result in unmatched:
            values = ", ".join(f"{v:g}" for v in result.unmatched[:12])
            lines.append(f"- `{result.label}`: {values}")
    lines += [
        "",
        "A number here is one the manuscript prints and the regenerated data does",
        "not contain. Check the analysis before you change the manuscript.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


MANIFEST_SKELETON = {
    "bindings": [
        {
            "label": "tab:results",
            "command": "python analysis/run.py --out results/results.json",
            "produces": "results/results.json",
            "tolerance": 0.005,
            "ignore": [],
        }
    ]
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-run the analysis behind each bound table or figure and reconcile its numbers."
    )
    parser.add_argument("--project-dir", default=".", help="Paper project directory (default: .).")
    parser.add_argument(
        "--manifest",
        default=None,
        help=f"Binding manifest (default: <project-dir>/notes/{MANIFEST_NAME}).",
    )
    parser.add_argument(
        "--no-run",
        action="store_true",
        help="Do not execute commands; compare against the outputs already on disk.",
    )
    parser.add_argument(
        "--timeout-s", type=float, default=600.0, help="Per-command timeout (default: 600)."
    )
    parser.add_argument(
        "--init", action="store_true", help="Write a manifest skeleton and exit."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        return fail("project dir not found")

    notes_dir = project_dir / "notes"
    manifest_path = Path(args.manifest) if args.manifest else notes_dir / MANIFEST_NAME

    if args.init:
        notes_dir.mkdir(parents=True, exist_ok=True)
        if manifest_path.exists():
            return fail(f"{manifest_path.name} already exists")
        manifest_path.write_text(
            json.dumps(MANIFEST_SKELETON, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{BANNER}: wrote notes/{manifest_path.name}")
        print("Bind every table and figure whose numbers come from a computation.")
        return 0

    main_tex = project_dir / "main.tex"
    if not main_tex.is_file():
        return fail("main.tex not found in project dir")
    if not manifest_path.is_file():
        print(f"{BANNER}: no notes/{MANIFEST_NAME}; nothing is bound to data.")
        print("Create one with: python scripts/data_gate.py --project-dir <dir> --init")
        return 0

    try:
        bindings = load_manifest(manifest_path)
    except (json.JSONDecodeError, ValueError) as exc:
        return fail(f"{manifest_path.name}: {exc}")

    if not bindings:
        print(f"{BANNER}: manifest has no bindings.")
        return 0

    tex_text = main_tex.read_text(encoding="utf-8", errors="replace")
    results = [
        check_binding(
            binding, project_dir, tex_text, run=not args.no_run, timeout_s=args.timeout_s
        )
        for binding in bindings
    ]

    notes_dir.mkdir(parents=True, exist_ok=True)
    write_report(notes_dir / "data-gate.md", results, ran=not args.no_run)

    for result in results:
        print(f"  [{result.status}] {result.label:<24} {result.detail}")
        for value in result.unmatched[:8]:
            print(f"          unmatched: {value:g}")

    failures = [r for r in results if r.status == "FAIL"]
    print(f"{BANNER}: {len(results) - len(failures)}/{len(results)} binding(s) reconcile")
    print("Report: notes/data-gate.md")
    if failures:
        print("A number the paper prints is not in the data the analysis produced.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
