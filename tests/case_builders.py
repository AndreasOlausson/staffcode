"""Deterministic Stackoda conformance programs built from a separate model."""

from __future__ import annotations

from dataclasses import dataclass
import random
import unicodedata

from reference_model import Bar, Branch, Note, Repeat, chord, constant, evaluate
from reference_model import flatten, key_signature as K, literal as P, navigation as N
from reference_model import operation as O, print_text, render, volta as V


@dataclass(frozen=True)
class Anchor:
    name: str
    nodes: tuple
    data: str
    output: str
    stack: tuple[int, ...]


@dataclass(frozen=True)
class Fixture:
    name: str
    score: str
    data: str
    output: str
    nodes: tuple | None


def anchors() -> tuple[Anchor, ...]:
    """Hand-pinned outcomes constrain the independent semantic model."""
    return (
        Anchor("empty-system", (), "", "", ()),
        Anchor("literal-chord", (chord(1, 9), O(9)), "", "10", ()),
        Anchor("dotted-chord", (chord(1, 9, dotted=True), O(9, dotted=True)), "", "1010", ()),
        Anchor("dot-sees-stack", (P(2), P(3), P(4), O(0, dotted=True), O(9)), "", "9", ()),
        Anchor("accidental-persists", (P(5, 1), O(7), P(5, None), O(9)), "", "6", ()),
        Anchor("bar-resets", (P(5, 1), O(7), Bar(), P(5, None), O(9)), "", "5", ()),
        Anchor("natural-replaces", (P(5, 1), O(7), P(5, 0), O(7), P(5, None), O(9)), "", "5", ()),
        Anchor(
            "key-signature-and-bar-reset",
            (K((5, 1), (2, -1)), P(5, None), O(9), P(2, None), O(9), P(5, 0), O(9), Bar(), P(5, None), O(9)),
            "",
            "6156",
            (),
        ),
        Anchor(
            "key-signature-replaces-whole-table",
            (K((5, 1), (4, -1)), K((5, 0)), P(5, None), O(9), P(4, None), O(9)),
            "",
            "54",
            (),
        ),
        Anchor(
            "note-accidental-does-not-change-key",
            (K((5, 1)), P(5, -1), O(9), Bar(), P(5, None), O(9)),
            "",
            "46",
            (),
        ),
        Anchor(
            "key-offsets-apply-to-every-note-family",
            (
                K((1, 1), (9, -1), (4, 1), (2, 1)),
                Note("push", ((1, None), (9, None))), O(9),
                P(7), O(4, accidental=None), O(9), O(9),
                O(2, "io", accidental=None), O(9),
            ),
            "12",
            "107712",
            (),
        ),
        Anchor(
            "skipped-conditional-key-has-no-effect",
            (K((5, 1)), P(0), Branch((K((5, -1)),)), Bar(), P(5, None), O(9)),
            "",
            "6",
            (),
        ),
        Anchor("skip-modifier", (P(0), Branch((P(5, 1), O(7))), P(5, None), O(9)), "", "5", ()),
        Anchor("skip-bar", (P(5, 1), O(7), P(0), Branch((Bar(),)), P(5, None), O(9)), "", "6", ()),
        Anchor("loop-state", (P(2), Repeat((P(5, None), O(9), P(5, 1), O(7)))), "", "56", ()),
        Anchor(
            "count-once",
            (P(3), Repeat((P(1),)), O(9), O(9), O(9), O(9)),
            "",
            "111",
            (),
        ),
        Anchor("empty-repeat-opener", (Repeat((P(8), O(9))), P(3), O(9)), "", "3", ()),
        Anchor("empty-if-opener", (Branch((P(8), O(9)), (P(4), O(9))),), "", "4", ()),
        Anchor("nested-repeats", (P(2), Repeat((P(3), Repeat((P(7), O(9)))))), "", "777777", ()),
        Anchor("fresh-inner-count", (P(2), P(1), P(2), Repeat((Repeat((P(7), O(9))),))), "", "777", ()),
        Anchor("negative-repeat", (P(0, -1), Repeat((P(7),)), O(9)), "", "", ()),
        Anchor(
            "volta-selects-and-reuses-last-ending",
            (P(3), Repeat((P(1), O(9), V(1), P(7), O(9), V(2), P(8), O(9)))),
            "",
            "171818",
            (),
        ),
        Anchor(
            "zero-repeat-skips-volta",
            (P(0), Repeat((P(1), O(9), V(1), P(7), O(9))), P(4), O(9)),
            "",
            "4",
            (),
        ),
        Anchor(
            "volta-state-crosses-passes",
            (
                P(2), Repeat((
                    P(5, None), O(9),
                    V(1), P(5, 1), O(7),
                    V(2), P(5, None), O(9),
                )),
            ),
            "",
            "566",
            (),
        ),
        Anchor(
            "volta-key-state-crosses-passes",
            (
                P(2), Repeat((
                    P(5, None), O(9),
                    V(1), K((5, 1)),
                    V(2), Bar(), P(5, None), O(9),
                )),
            ),
            "",
            "566",
            (),
        ),
        Anchor(
            "nested-volta-pass-counts-are-fresh",
            (
                P(2), Repeat((
                    P(2), Repeat((P(1), O(9), V(1), P(7), O(9), V(2), P(8), O(9))),
                )),
            ),
            "",
            "17181718",
            (),
        ),
        Anchor(
            "volta-keeps-conditional-structure",
            (
                P(2), Repeat((
                    V(1), P(0), Branch((P(8), O(9)), (P(4), O(9))),
                    V(2), P(1), Branch((P(8), O(9)), (P(4), O(9))),
                )),
            ),
            "",
            "48",
            (),
        ),
        Anchor(
            "navigation-replays-all-volta-endings",
            (
                N("segno"),
                P(2), Repeat((P(1), O(9), V(1), P(7), O(9), V(2), P(8), O(9))),
                N("to-coda"), N("dal-segno"), N("coda"),
            ),
            "",
            "1718178",
            (2,),
        ),
        Anchor(
            "navigation-preserves-key-state",
            (
                K((5, 1)), N("segno"), P(5, None), O(9), N("to-coda"),
                K((5, -1)), N("dal-segno"), N("coda"), P(5, None), O(9),
            ),
            "",
            "644",
            (),
        ),
        Anchor(
            "navigation-replays-key-events",
            (
                N("segno"), K((5, 1)), P(5, None), O(9), N("to-coda"),
                K((5, -1)), N("dal-segno"), N("coda"), P(5, None), O(9),
            ),
            "",
            "666",
            (),
        ),
        Anchor(
            "dal-segno-once",
            (P(1), O(9), N("segno"), P(2), O(9), N("dal-segno"), P(3), O(9)),
            "",
            "1223",
            (),
        ),
        Anchor(
            "coda-jump",
            (
                P(1), O(9), N("segno"), P(2), O(9), N("to-coda"),
                P(3), O(9), N("dal-segno"), P(4), O(9), N("coda"), P(5), O(9),
            ),
            "",
            "12325",
            (),
        ),
        Anchor(
            "navigation-keeps-accidentals",
            (
                N("segno"), P(5, None), O(9), N("to-coda"), P(5, 1), O(7),
                N("dal-segno"), N("coda"), P(5, None), O(9),
            ),
            "",
            "566",
            (),
        ),
        Anchor(
            "segno-keeps-accidentals",
            (
                P(5, 1), O(7), N("segno"), P(5, None), O(9), N("to-coda"),
                N("dal-segno"), N("coda"),
            ),
            "",
            "66",
            (),
        ),
        Anchor(
            "segno-keeps-input-cursor",
            (
                O(4, "io"), O(7), N("segno"), O(4, "io"), O(8),
                N("to-coda"), N("dal-segno"), N("coda"),
            ),
            "abc",
            "bc",
            (),
        ),
        Anchor(
            "replay-bar-resets-accidentals",
            (
                N("segno"), P(5, 1), O(7), Bar(), P(5, None), O(9),
                N("to-coda"), N("dal-segno"), N("coda"),
            ),
            "",
            "55",
            (),
        ),
        Anchor(
            "navigation-keeps-input-cursor",
            (
                N("segno"), O(4, "io"), O(8), N("to-coda"), O(4, "io"), O(8),
                N("dal-segno"), N("coda"), O(4, "io"), O(8),
            ),
            "abcd",
            "abcd",
            (),
        ),
        Anchor(
            "navigation-keeps-stack",
            (
                P(4), N("segno"), O(9), N("to-coda"), P(7),
                N("dal-segno"), N("coda"),
            ),
            "",
            "47",
            (),
        ),
        Anchor(
            "coda-jump-keeps-stack",
            (
                N("segno"), P(7), N("to-coda"), O(7),
                N("dal-segno"), N("coda"), O(9),
            ),
            "",
            "7",
            (),
        ),
        Anchor(
            "replay-ignores-repeat",
            (
                N("segno"), P(2), Repeat((P(7), O(9))), N("to-coda"),
                N("dal-segno"), N("coda"), O(9),
            ),
            "",
            "7772",
            (),
        ),
        Anchor(
            "replay-ignores-nested-repeats",
            (
                N("segno"), P(2), Repeat((P(3), Repeat((P(7), O(9))))),
                N("to-coda"), N("dal-segno"), N("coda"), O(9), O(9),
            ),
            "",
            "777777732",
            (),
        ),
        Anchor(
            "replay-keeps-conditionals",
            (
                N("segno"), P(0), Branch((P(8), O(9)), (P(4), O(9))),
                N("to-coda"), N("dal-segno"), N("coda"),
            ),
            "",
            "44",
            (),
        ),
        Anchor(
            "post-coda-repeat-is-normal",
            (
                N("segno"), N("to-coda"), N("dal-segno"), N("coda"),
                P(2), Repeat((P(8), O(9))),
            ),
            "",
            "88",
            (),
        ),
        Anchor(
            "post-dal-segno-repeat-is-normal",
            (N("segno"), N("dal-segno"), P(2), Repeat((P(8), O(9)))),
            "",
            "88",
            (),
        ),
        Anchor("nested-skip", (P(0), Branch((P(2), Repeat((P(1), Branch((P(9),), (P(8),))))), (P(4),)), O(9)), "", "4", ()),
        Anchor("underflow-atomic", (P(3), O(0), O(6), O(9)), "", "3", ()),
        Anchor("subtract-underflow", (P(7), O(1), O(9)), "", "7", ()),
        Anchor("multiply-underflow", (P(7), O(2), O(9)), "", "7", ()),
        Anchor("divide-underflow", (P(7), O(3), O(9)), "", "7", ()),
        Anchor("modulo-underflow", (P(7), O(4), O(9)), "", "7", ()),
        Anchor("empty-duplicate", (O(5), O(9)), "", "", ()),
        Anchor("empty-drop", (O(7), P(7), O(9), O(9)), "", "7", ()),
        Anchor("zero-division", (P(7), P(0), O(3), O(9), O(9)), "", "07", ()),
        Anchor("floor-division", (*constant(-7), P(3), O(3), O(9)), "", "-3", ()),
        Anchor("negative-modulo", (*constant(-7), P(3), O(4), O(9)), "", "2", ()),
        Anchor("negative-divisor", (P(7), *constant(-3), O(4), O(9)), "", "-2", ()),
        Anchor("operand-order", (P(8), P(3), O(1), O(9)), "", "5", ()),
        Anchor("comparison-order", (P(8), P(3), O(1, "io"), O(9)), "", "1", ()),
        Anchor("equal-not", (P(3), P(3), O(0, "io"), O(2, "io"), O(9)), "", "0", ()),
        Anchor("shared-input", (O(3, "io"), O(9), O(4, "io"), O(8)), "  -12X", "-12X", ()),
        Anchor(
            "all-ascii-whitespace",
            (O(3, "io"), O(9), O(4, "io"), O(8)),
            "\t\r\v\f\n -12X",
            "-12X",
            (),
        ),
        Anchor("non-ascii-digit", (O(3, "io"), O(4, "io"), O(9)), "١2", "1633", ()),
        Anchor("non-ascii-whitespace", (O(3, "io"), O(4, "io"), O(9)), "\u00a012", "160", ()),
        Anchor("failed-read-rollback", (O(3, "io"), O(4, "io"), O(9)), "  +x", "32", ()),
        Anchor("unicode-character", (O(4, "io"), O(8)), "𝄞", "𝄞", ()),
        Anchor("eof-noop", (P(7), O(3, "io"), O(4, "io"), O(9)), "", "7", ()),
        Anchor("invalid-scalar", (*constant(0xD800), O(8), O(9)), "", "55296", ()),
        Anchor("invalid-scalar-interior", (*constant(0xDEAD), O(8), O(9)), "", "57005", ()),
        Anchor("invalid-scalar-upper", (*constant(0xDFFF), O(8), O(9)), "", "57343", ()),
        Anchor("reserved-selector", (P(7), O(9, accidental=1), O(9)), "", "7", ()),
        Anchor("reserved-io-five", (P(7), O(5, "io"), O(9), O(9)), "", "7", ()),
        Anchor("reserved-io-six", (P(2), P(7), O(6, "io"), O(9), O(9)), "", "72", ()),
        Anchor("reserved-io-seven", (P(2), P(7), O(7, "io"), O(9), O(9)), "", "72", ()),
        Anchor("reserved-io-eight", (P(5), chord(1, 9), O(2), P(5), O(0), O(8, "io"), O(9)), "", "55", ()),
        Anchor("reserved-io-nine", (P(7), O(9, "io"), P(3), O(0), O(9)), "", "10", ()),
        Anchor("modifier-selects-op", (P(2), P(3), O(1, accidental=1), O(9)), "", "6", ()),
        Anchor("modified-chord", (Note("push", ((8, 1), (9, -1))), O(9)), "", "17", ()),
        Anchor("negative-chord", (Note("push", ((0, -1), (1, -1))), O(9), P(0, None), O(9)), "", "-1-1", ()),
        Anchor("persisted-selector", (P(8), P(3), O(0, accidental=1), O(9), P(9), P(4), O(0, accidental=None), O(9)), "", "55", ()),
        Anchor("dotted-read-int", (O(3, "io", dotted=True), O(9), O(9)), " 4 -5x", "-54", ()),
        Anchor("dotted-read-char", (O(4, "io", dotted=True), O(8), O(8)), "ab", "ba", ()),
        Anchor("dotted-underflow", (P(3), P(4), O(0, dotted=True), O(9)), "", "7", ()),
        Anchor("not-empty", (O(2, "io"), O(9)), "", "", ()),
        Anchor("not-values", (P(0), O(2, "io"), O(9), P(5), O(2, "io"), O(9)), "", "10", ()),
        Anchor("write-max-scalar", (*constant(0x10FFFF), O(8)), "", "\U0010FFFF", ()),
        Anchor("write-beyond-scalar", (*constant(0x110000), O(8), O(9)), "", "1114112", ()),
        Anchor("write-negative", (*constant(-1), O(8), O(9)), "", "-1", ()),
        Anchor("sign-without-digits", (O(3, "io"), O(4, "io"), O(8)), "+-5", "+", ()),
        Anchor("whitespace-eof", (O(3, "io"), O(4, "io"), O(9)), "  \n", "32", ()),
        Anchor("digits-then-text", (O(3, "io"), O(9), O(4, "io"), O(8)), "12abc", "12a", ()),
        Anchor("long-leading-zeros", (P(7), O(9), O(3, "io"), O(9)), "0" * 4095 + "7", "77", ()),
        Anchor(
            "arbitrary-precision",
            (*constant((1 << 130) + 12_345), O(9)),
            "",
            str((1 << 130) + 12_345),
            (),
        ),
        Anchor("taken-else-state", (P(5, 1), O(7), P(0), Branch((P(9), O(7)), (Bar(), P(5, -1), O(7))), P(5, None), O(9)), "", "4", ()),
        Anchor("skipped-zero-repeat", (P(5, 1), O(7), P(0), Repeat((Bar(), P(5, -1), O(7))), P(5, None), O(9)), "", "6", ()),
    )


def random_program(seed: int) -> tuple:
    """Generate bounded interacting programs from a fixed seed."""
    rng = random.Random(seed)

    def block(depth: int) -> tuple:
        nodes = []
        for _ in range(rng.randint(6, 15)):
            choice = rng.randrange(8 if depth else 6)
            if choice == 0:
                nodes.append(Bar())
            elif choice == 1:
                ranks = rng.sample(range(10), rng.randint(1, 4))
                nodes.append(Note("push", tuple((r, rng.choice((None, -1, 0, 1))) for r in ranks), rng.random() < 0.25))
            elif choice in (2, 3):
                mark = rng.choice((None, -1, 0, 1))
                selectors = (0, 1, 3, 4, 5, 6, 7, 8, 9) if mark == 0 else (0, 4, 5, 6, 7, 8, 9)
                nodes.append(O(rng.choice(selectors), accidental=mark, dotted=rng.random() < 0.25))
            elif choice == 4:
                nodes.append(O(rng.randrange(5), "io", accidental=rng.choice((None, -1, 0, 1)), dotted=rng.random() < 0.25))
            elif choice == 5:
                nodes.append(P(rng.randrange(10), rng.choice((None, -1, 0, 1))))
            elif choice == 6:
                nodes.extend((P(rng.randrange(3)), Repeat(block(depth - 1))))
            else:
                nodes.extend((P(rng.randrange(2)), Branch(block(depth - 1), block(depth - 1))))
        return tuple(nodes)

    return block(2)


def navigation_program(seed: int) -> tuple:
    """Generate a navigation case with state changes on both passes."""
    rng = random.Random(seed)
    row = rng.randrange(10)
    repeat_value = rng.choice((6, 7, 8, 9))
    branch_value = rng.choice((3, 4, 5, 6))
    condition = rng.randrange(2)
    middle_state = Bar() if rng.random() < 0.5 else P(row, rng.choice((-1, 1)))
    if not isinstance(middle_state, Bar):
        middle = (middle_state, O(7))
    else:
        middle = (middle_state,)
    return (
        P(rng.randrange(10)),
        O(7),
        N("segno"),
        P(row, None),
        O(9),
        P(rng.choice((2, 3))),
        Repeat((P(repeat_value), O(9))),
        O(4, "io"),
        O(8),
        P(condition),
        Branch((P(branch_value), O(9)), (P(9 - branch_value), O(9))),
        N("to-coda"),
        *middle,
        O(4, "io"),
        O(8),
        N("dal-segno"),
        *print_text("DEAD"),
        N("coda"),
        P(row, None),
        O(9),
        P(2),
        Repeat((P(9 - repeat_value), O(9))),
    )


def volta_program(seed: int) -> tuple:
    """Generate nested volta selection with persistent state and input."""
    rng = random.Random(seed)
    row = rng.randrange(10)
    first = rng.choice((6, 7, 8, 9))
    second = rng.choice(tuple(value for value in (5, 6, 7, 8) if value != first))
    count = rng.choice((2, 3, 4))
    return (
        P(count),
        Repeat((
            P(row, None), O(9), O(4, "io"), O(8),
            V(1), P(row, 1), O(7), P(first), O(9),
            V(2), P(2), Repeat((P(second), O(9))),
            V(3), Bar(), P(row, None), O(9),
        )),
    )


def key_volta_program(seed: int) -> tuple:
    """Generate key changes whose effects depend on volta selection and bars."""
    rng = random.Random(seed)
    row = rng.randrange(10)
    other = (row + rng.randrange(1, 10)) % 10
    count = rng.choice((2, 3, 4))
    return (
        K((row, rng.choice((-1, 1))), (other, rng.choice((-1, 1)))),
        P(count),
        Repeat((
            P(row, None), O(9),
            V(1), K((row, 1)), P(row, None), O(9),
            V(2), P(row, 0), O(9), Bar(), P(row, None), O(9),
            V(3), K((row, -1), (other, 0)), P(row, None), O(9),
        )),
        Bar(), P(other, None), O(9),
    )


def _step_boundary_program() -> tuple:
    """Build a valid program whose execution is exactly 100,000 steps."""
    nodes = (*constant(99_982), Repeat(()))
    assert evaluate(nodes).steps == 100_000
    return nodes


def conformance_cases() -> tuple[Fixture, ...]:
    result = [Fixture("zero-byte", "", "", "", None)]
    spellings = ("composed", "decomposed", "mixed")
    for index, anchor in enumerate(anchors()):
        event_count = len(flatten(anchor.nodes))
        per_system = max((index % 13) + 1, (event_count + 127) // 128)
        score = render(anchor.nodes, seed=7000 + index, per_system=per_system, spelling=spellings[index % 3])
        result.append(Fixture(anchor.name, score, anchor.data, anchor.output, anchor.nodes))

    data = "  -12X +4\n𝄞 7 ?"
    for index, seed in enumerate((1011, 1066, 1096, 1172, 1194, 1236, 1243, 1291)):
        nodes = random_program(seed)
        state = evaluate(nodes, data)
        score = render(nodes, seed=9000 + seed, per_system=(7, 11, 17)[index % 3], spelling=spellings[index % 3])
        result.append(Fixture(f"combined-{seed}", score, data, state.output, nodes))

    for index, seed in enumerate((3101, 3127, 3163, 3209, 3251, 3299)):
        nodes = navigation_program(seed)
        data = "a𝄞Z"
        state = evaluate(nodes, data)
        score = render(nodes, seed=15000 + seed, per_system=(6, 10, 15)[index % 3], spelling=spellings[index % 3])
        result.append(Fixture(f"navigation-{seed}", score, data, state.output, nodes))

    for index, seed in enumerate((4103, 4153, 4211, 4271, 4337, 4391)):
        nodes = volta_program(seed)
        data = "abcdef"
        state = evaluate(nodes, data)
        score = render(nodes, seed=17000 + seed, per_system=(5, 9, 14)[index % 3], spelling=spellings[index % 3])
        result.append(Fixture(f"volta-{seed}", score, data, state.output, nodes))

    for index, seed in enumerate((5101, 5153, 5227, 5281, 5347, 5413)):
        nodes = key_volta_program(seed)
        state = evaluate(nodes)
        score = render(nodes, seed=19000 + seed, per_system=(5, 8, 13)[index % 3], spelling=spellings[index % 3])
        result.append(Fixture(f"key-volta-{seed}", score, "", state.output, nodes))

    nodes = (*print_text("NFD≠INPUT:"), O(4, "io"), O(8), O(4, "io"), O(8))
    state = evaluate(nodes, "e\u0301")
    result.append(Fixture("input-not-normalized", render(nodes, 9911, 9, "decomposed"), "e\u0301", state.output, nodes))

    nodes = (O(4, "io"), O(8))
    result.append(Fixture("composed-input-not-normalized", render(nodes, 9912, 9, "mixed"), "é", "é", nodes))

    boundary = _step_boundary_program()
    result.append(Fixture("step-boundary", render(boundary, 9922, 19, "mixed"), "", "", boundary))
    return tuple(result)


def all_sources_within_envelope(fixtures: tuple[Fixture, ...]) -> bool:
    combining = {"\U0001D165", *map(chr, range(0x1D16E, 0x1D173))}

    def row_cells(row: str) -> list[str]:
        result = []
        for character in unicodedata.normalize("NFD", row):
            if character in combining:
                if not result:
                    return []
                result[-1] += character
            else:
                result.append(character)
        return result

    def depth(nodes: tuple, current: int = 0) -> int:
        maximum = current
        for node in nodes:
            if isinstance(node, Repeat):
                maximum = max(maximum, depth(node.body, current + 1))
            elif isinstance(node, Branch):
                maximum = max(maximum, depth(node.yes, current + 1), depth(node.no or (), current + 1))
        return maximum

    for fixture in fixtures:
        if len(fixture.score) > 200_000 or len(fixture.data.encode("utf-8")) > 65_536:
            return False
        if fixture.score:
            systems = fixture.score[:-1].split("\n\n")
            if len(systems) > 128:
                return False
            for system in systems:
                lines = system.splitlines()
                if len(lines) != 11 or lines[0] != "STAFF":
                    return False
                widths = [len(row_cells(row)) - 2 for row in lines[1:]]
                if len(set(widths)) != 1 or not 0 <= widths[0] <= 8_192:
                    return False
        if fixture.nodes is not None:
            state = evaluate(fixture.nodes, fixture.data)
            if (
                state.steps > 100_000
                or state.peak_stack > 4_096
                or state.peak_bits > 4_096
                or depth(fixture.nodes) > 64
                or len(state.output.encode("utf-8")) > 65_536
            ):
                return False
    return True
