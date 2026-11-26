"""Every relative link and image in README.md and docs/*.md must point to a file that exists; no AI-vendor names in published text."""
import re
from pathlib import Path
import pytest
from src.config import ROOT

DOCS = [ROOT / "README.md", ROOT / "CHANGELOG.md", *sorted((ROOT / "docs").glob("*.md")), ROOT / "reports" / "README.md"]


@pytest.mark.parametrize("md", DOCS, ids=lambda p: p.name)
def test_relative_links_resolve(md):
    text = md.read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.S)                  # ignore code blocks
    bad = []
    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path = (md.parent / target.split("#")[0]).resolve()
        if not path.exists():
            bad.append(target)
    assert not bad, f"{md.name}: broken links {bad}"


def test_images_are_real_screenshots_not_blank():
    from PIL import Image
    import numpy as np
    for f in (ROOT / "docs" / "img").glob("*.png"):
        a = np.asarray(Image.open(f).convert("L"))
        assert (a < 245).mean() > 0.01, f"{f.name} looks blank"


def test_no_ai_vendor_or_coauthor_text_in_published_docs():
    banned = re.compile(r"claude|sonnet|chatgpt|co-authored-by|generated with", re.I)
    for md in DOCS:
        assert not banned.search(md.read_text(encoding="utf-8")), md.name
