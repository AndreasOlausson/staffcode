from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unicodedata

import pytest

from case_builders import all_sources_within_envelope, anchors, conformance_cases
from reference_model import evaluate, render
from staffcode import execute, parse


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
FIXTURES = conformance_cases()


@pytest.mark.parametrize("score", sorted(EXAMPLES.glob("*.staff")), ids=lambda path: path.stem)
def test_examples(score: Path) -> None:
    data = score.with_suffix(".in").read_text(encoding="utf-8")
    expected = score.with_suffix(".out").read_text(encoding="utf-8")
    output, _, _ = execute(parse(score.read_text(encoding="utf-8")), data)
    assert output == expected


def test_frozen_semantic_anchors() -> None:
    for anchor in anchors():
        state = evaluate(anchor.nodes, anchor.data)
        assert (state.output, tuple(state.values)) == (anchor.output, anchor.stack), anchor.name


def test_generated_conformance_fixtures() -> None:
    assert len(FIXTURES) >= 100
    assert all_sources_within_envelope(FIXTURES)
    for fixture in FIXTURES:
        output, _, _ = execute(parse(fixture.score), fixture.data)
        assert output == fixture.output, fixture.name


def test_canonical_note_spellings() -> None:
    candidates = [anchor for anchor in anchors() if anchor.output]
    for anchor in candidates[:: max(1, len(candidates) // 8)]:
        variants = [render(anchor.nodes, 4242, 5, spelling) for spelling in ("composed", "decomposed", "mixed")]
        normalized = [unicodedata.normalize("NFD", score) for score in variants]
        assert normalized[0] == normalized[1] == normalized[2]
        for score in variants:
            output, _, _ = execute(parse(score), anchor.data)
            assert output == anchor.output


def test_module_cli() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "staffcode", str(EXAMPLES / "mozart.staff")],
        check=False,
        capture_output=True,
    )
    assert result.returncode == 0
    assert result.stdout == b"Mozart"
    assert result.stderr == b""


def test_inspect_cli() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "staffcode", "inspect", str(EXAMPLES / "chord.staff")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "push" in result.stdout
    assert "op" in result.stdout
