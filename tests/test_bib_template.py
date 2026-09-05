"""Regression tests for assets/template/references.template.bib.

The template .bib is copied into every scaffolded project as `ref.bib`, so a
defect here breaks the very first command a new user runs
(`compile_paper.py` on a freshly bootstrapped paper).

BibTeX has no notion of a trailing comment. A `%` after a field value does not
end a comment at the newline — it makes BibTeX report "You're missing a field
name" and skip the rest of the entry, leaving citations undefined. The failure
surfaces only in `main.blg`, which nobody reads.
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_BIB = SKILL_DIR / "assets" / "template" / "references.template.bib"

# A field line inside an entry: whitespace, name, '=', value, then a stray '%'.
_TRAILING_COMMENT_RE = re.compile(r"^\s+[A-Za-z]+\s*=.*%", re.MULTILINE)
_ENTRY_RE = re.compile(r"^@(\w+)\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)


class TestReferencesTemplate(unittest.TestCase):
    def test_template_exists(self) -> None:
        self.assertTrue(TEMPLATE_BIB.exists(), msg=f"{TEMPLATE_BIB} should exist")

    def test_no_trailing_comment_after_a_field(self) -> None:
        text = TEMPLATE_BIB.read_text(encoding="utf-8")
        offenders = [m.group(0).strip()[:90] for m in _TRAILING_COMMENT_RE.finditer(text)]
        self.assertEqual(
            offenders,
            [],
            msg=(
                "BibTeX cannot parse a '%' comment after a field value; it skips the whole "
                "entry. Put the comment on its own line above the entry.\nOffending lines:\n  "
                + "\n  ".join(offenders)
            ),
        )

    def test_entry_keys_are_unique(self) -> None:
        keys = [m.group(2) for m in _ENTRY_RE.finditer(TEMPLATE_BIB.read_text(encoding="utf-8"))]
        duplicates = {key for key in keys if keys.count(key) > 1}
        self.assertEqual(duplicates, set(), msg=f"duplicate citation keys: {sorted(duplicates)}")

    def test_braces_are_balanced(self) -> None:
        text = TEMPLATE_BIB.read_text(encoding="utf-8")
        body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("%"))
        self.assertEqual(
            body.count("{"), body.count("}"), msg="unbalanced braces in references.template.bib"
        )

    def test_bibtex_parses_every_entry(self) -> None:
        """Run the real bibtex over the template and require a clean parse."""
        bibtex = shutil.which("bibtex")
        if not bibtex:
            self.skipTest("bibtex not available")

        keys = [m.group(2) for m in _ENTRY_RE.finditer(TEMPLATE_BIB.read_text(encoding="utf-8"))]
        self.assertTrue(keys, msg="template contains no entries")

        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            shutil.copy(TEMPLATE_BIB, work / "ref.bib")
            # A minimal .aux is enough to drive bibtex; no LaTeX run needed.
            aux = ["\\relax", "\\bibstyle{plain}"]
            aux += [f"\\citation{{{key}}}" for key in keys]
            aux.append("\\bibdata{ref}")
            (work / "main.aux").write_text("\n".join(aux) + "\n", encoding="utf-8")

            subprocess.run(
                [bibtex, "main"],
                cwd=str(work),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
            )

            blg = (work / "main.blg").read_text(encoding="utf-8", errors="replace")
            self.assertNotIn("missing a field name", blg, msg=f"bibtex log:\n{blg}")
            self.assertNotIn("I'm skipping whatever remains", blg, msg=f"bibtex log:\n{blg}")

            bbl = (work / "main.bbl").read_text(encoding="utf-8", errors="replace")
            for key in keys:
                with self.subTest(key=key):
                    self.assertIn(
                        f"\\bibitem{{{key}}}",
                        bbl,
                        msg=f"'{key}' did not survive bibtex; see the .blg output",
                    )


if __name__ == "__main__":
    unittest.main()
