"""Author-side score builder and independent recursive semantic evaluator."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
import unicodedata

# Precomposed note spellings; NFD turns each into notehead, stem and flag.
GLYPHS = {"push": "\U0001D15F", "op": "\U0001D160", "io": "\U0001D15E"}


@dataclass(frozen=True)
class Note:
    family: str
    tones: tuple[tuple[int, int | None], ...]
    dotted: bool = False


@dataclass(frozen=True)
class Bar:
    pass


@dataclass(frozen=True)
class KeySignature:
    entries: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class Repeat:
    body: tuple


@dataclass(frozen=True)
class Volta:
    number: int


@dataclass(frozen=True)
class Branch:
    yes: tuple
    no: tuple | None = None


@dataclass(frozen=True)
class Navigation:
    kind: str


def literal(value: int, accidental: int | None = 0, dotted: bool = False) -> Note:
    return Note("push", ((value, accidental),), dotted)


def operation(value: int, family: str = "op", accidental: int | None = 0, dotted: bool = False) -> Note:
    return Note(family, ((value, accidental),), dotted)


def chord(*values: int, dotted: bool = False) -> Note:
    return Note("push", tuple((value, 0) for value in values), dotted)


def key_signature(*entries: tuple[int, int]) -> KeySignature:
    if len({rank for rank, _ in entries}) != len(entries):
        raise ValueError("duplicate key-signature row")
    if any(rank not in range(10) or offset not in (-1, 0, 1) for rank, offset in entries):
        raise ValueError(entries)
    return KeySignature(tuple(entries))


def navigation(kind: str) -> Navigation:
    if kind not in {"segno", "dal-segno", "to-coda", "coda"}:
        raise ValueError(kind)
    return Navigation(kind)


def volta(number: int) -> Volta:
    if number not in range(1, 5):
        raise ValueError(number)
    return Volta(number)


def constant(value: int) -> tuple:
    digits = str(abs(value))
    code = [literal(int(digits[0]))]
    for digit in digits[1:]:
        code.extend((chord(1, 9), operation(2), literal(int(digit)), operation(0)))
    if value < 0:
        code.extend((literal(0), operation(6), operation(1)))
    return tuple(code)


def print_text(text: str) -> tuple:
    code = []
    for char in text:
        code.extend(constant(ord(char)))
        code.append(operation(8))
    return tuple(code)


def flatten(nodes: tuple) -> list:
    events = []
    for node in nodes:
        if isinstance(node, Note):
            events.append(node)
        elif isinstance(node, Bar):
            events.append("bar")
        elif isinstance(node, KeySignature):
            events.append(node)
        elif isinstance(node, Repeat):
            events.extend(["repeat", *flatten(node.body), "end"])
        elif isinstance(node, Volta):
            events.append(f"volta-{node.number}")
        elif isinstance(node, Branch):
            events.extend(["if", *flatten(node.yes)])
            if node.no is not None:
                events.extend(["else", *flatten(node.no)])
            events.append("fi")
        elif isinstance(node, Navigation):
            events.append(node.kind)
        else:
            raise TypeError(node)
    return events


def render(nodes: tuple, seed: int = 0, per_system: int = 14, spelling: str = "composed") -> str:
    """Lay out a score; spelling is "composed", "decomposed" or per-note "mixed"."""
    rng = random.Random(seed)
    # A separate generator keeps layouts identical across spellings.
    speller = random.Random(seed)
    events = flatten(nodes)
    chunks = [events[i : i + per_system] for i in range(0, len(events), per_system)] or [[]]
    systems = []
    marks = {-1: "♭", 0: "♮", 1: "♯"}
    controls = {
        "repeat": "𝄆",
        "end": "𝄇",
        "if": "?",
        "else": ":",
        "fi": ";",
        "segno": "𝄋",
        "dal-segno": "𝄉",
        "to-coda": "@",
        "coda": "𝄌",
        "volta-1": "①",
        "volta-2": "②",
        "volta-3": "③",
        "volta-4": "④",
    }
    for chunk in chunks:
        positions = []
        column = rng.randint(1, 3)
        for event in chunk:
            positions.append(column)
            column += rng.randint(4, 7)
        width = column + 2
        grid = [["-" if row % 2 else " "] * width for row in range(10)]
        for event, column in zip(chunk, positions):
            if event == "bar":
                for row in grid:
                    row[column] = "|"
            elif isinstance(event, KeySignature):
                grid[5][column] = "𝄞"
                for rank, offset in event.entries:
                    grid[9 - rank][column + 1] = marks[offset]
            elif isinstance(event, str):
                grid[5][column] = controls[event]
            else:
                for rank, accidental in event.tones:
                    row = 9 - rank
                    glyph = GLYPHS[event.family]
                    if spelling == "decomposed" or (spelling == "mixed" and speller.random() < .5):
                        glyph = unicodedata.normalize("NFD", glyph)
                    grid[row][column] = glyph
                    if accidental is not None:
                        grid[row][column - 1] = marks[accidental]
                    if event.dotted:
                        grid[row][column + 1] = "."
        systems.append("STAFF\n" + "\n".join("|" + "".join(row) + "|" for row in grid))
    return "\n\n".join(systems) + "\n"


@dataclass
class State:
    data: str = ""
    values: list[int] = field(default_factory=list)
    key_marks: dict[int, int] = field(default_factory=dict)
    marks: dict[int, int] = field(default_factory=dict)
    output: str = ""
    cursor: int = 0
    steps: int = 0
    peak_stack: int = 0
    peak_bits: int = 0


STEP_LIMIT = 100_000


def evaluate(nodes: tuple, data: str = "", mutant: str = "") -> State:
    state = State(data=data)

    def tick(amount: int = 1) -> None:
        # Every step goes through here so no path can exceed the envelope.
        state.steps += amount
        if state.steps > STEP_LIMIT:
            raise ValueError("author probe exceeded its execution budget")

    def take(default: int = 0) -> int:
        return state.values.pop() if state.values else default

    def preapply(block: tuple) -> None:
        for event in flatten(block):
            if isinstance(event, Note):
                for rank, mark in event.tones:
                    if mark is not None:
                        state.marks[rank] = mark
            elif event == "bar":
                state.marks = state.key_marks.copy()
            elif isinstance(event, KeySignature):
                state.key_marks = {rank: offset for rank, offset in event.entries if offset}
                state.marks = state.key_marks.copy()

    def action(family: str, selector: int) -> None:
        stack = state.values
        if family == "push":
            stack.append(selector)
            return
        if family == "op" and 0 <= selector <= 4:
            if len(stack) < 2 or (selector in (3, 4) and stack[-1] == 0):
                return
            right, left = stack.pop(), stack.pop()
            if selector == 0:
                result = left + right
            elif selector == 1:
                result = left - right
            elif selector == 2:
                result = left * right
            else:
                quotient = abs(left) // abs(right)
                if (left < 0) != (right < 0):
                    quotient = -quotient
                if mutant != "truncate-division" and left != quotient * right and (left < 0) != (right < 0):
                    quotient -= 1
                result = quotient if selector == 3 else left - quotient * right
            stack.append(result)
        elif family == "op" and selector == 5 and stack:
            stack.append(stack[-1])
        elif family == "op" and selector == 6 and len(stack) >= 2:
            top = stack.pop()
            below = stack.pop()
            stack.extend((top, below))
        elif family == "op" and selector == 7:
            take()
        elif family == "op" and selector == 8 and stack:
            number = stack[-1]
            if 0 <= number < 0x110000 and number not in range(0xD800, 0xE000):
                state.output += chr(stack.pop())
        elif family == "op" and selector == 9 and stack:
            state.output += str(stack.pop())
        elif family == "io" and selector in (0, 1) and len(stack) >= 2:
            right, left = stack.pop(), stack.pop()
            stack.append(int(left == right) if selector == 0 else int(left > right))
        elif family == "io" and selector == 2 and stack:
            stack.append(int(stack.pop() == 0))
        elif family == "io" and selector == 2 and mutant == "empty-not-is-one":
            stack.append(1)
        elif family == "io" and selector == 3:
            start = state.cursor
            pointer = start
            while pointer < len(data) and data[pointer] in " \t\r\n\v\f":
                pointer += 1
            sign = 1
            if pointer < len(data) and data[pointer] in "+-":
                sign = -1 if data[pointer] == "-" else 1
                pointer += 1
            first_digit = pointer
            number = 0
            while pointer < len(data) and "0" <= data[pointer] <= "9":
                number = number * 10 + ord(data[pointer]) - ord("0")
                pointer += 1
            if pointer != first_digit:
                state.cursor = pointer
                stack.append(sign * number)
            elif mutant == "consume-failed-input":
                state.cursor = pointer
        elif family == "io" and selector == 4 and state.cursor < len(data):
            stack.append(ord(data[state.cursor]))
            state.cursor += 1

    def walk(block: tuple, replay: bool = False) -> None:
        # Steps follow the SPEC envelope: one per note half, barline, opener and
        # completed repetition iteration; ending labels, `:`, `;` and `𝄇` add nothing.
        for node in block:
            if isinstance(node, Volta):
                if replay:
                    continue
                raise ValueError("volta label outside its repeat dispatcher")
            tick()
            if isinstance(node, Bar):
                if mutant != "ignore-bars":
                    state.marks = state.key_marks.copy()
            elif isinstance(node, KeySignature):
                state.key_marks = {rank: offset for rank, offset in node.entries if offset}
                state.marks = state.key_marks.copy()
            elif isinstance(node, Repeat):
                if replay:
                    walk(node.body, replay=True)
                else:
                    count = max(0, take())
                    if mutant == "execute-skipped-marks" and count == 0:
                        preapply(node.body)
                    saved = state.marks.copy()
                    prefix = []
                    endings: list[list] = []
                    current = prefix
                    for item in node.body:
                        if isinstance(item, Volta):
                            if item.number != len(endings) + 1:
                                raise ValueError("volta labels must be contiguous")
                            endings.append([])
                            current = endings[-1]
                        else:
                            current.append(item)
                    for iteration in range(count):
                        if mutant == "restore-loop-marks":
                            state.marks = saved.copy()
                        if endings:
                            walk(tuple(prefix))
                            walk(tuple(endings[min(iteration, len(endings) - 1)]))
                        else:
                            walk(node.body)
                        tick()
            elif isinstance(node, Branch):
                choose_yes = take() != 0
                if mutant == "execute-skipped-marks":
                    preapply(node.no or () if choose_yes else node.yes)
                walk(node.yes if choose_yes else node.no or (), replay=replay)
            elif isinstance(node, Note):
                for rank, mark in node.tones:
                    if mark is not None:
                        state.marks[rank] = mark
                values = [rank + state.marks.get(rank, 0) for rank, _ in node.tones]
                value = sum(values)
                times = 2 if node.dotted else 1
                if mutant == "scale-dotted-literal" and node.family == "push" and node.dotted:
                    value *= 2
                    times = 1
                for _ in range(times):
                    if mutant == "split-chords" and node.family == "push":
                        for item in values:
                            action("push", item)
                    else:
                        action(node.family, value)
                    state.peak_stack = max(state.peak_stack, len(state.values))
                    state.peak_bits = max(
                        [state.peak_bits, *(abs(item).bit_length() for item in state.values)]
                    )
                tick(times - 1)
            elif isinstance(node, Navigation):
                raise ValueError("navigation markers must be at the top level")
            else:
                raise TypeError(node)

    navigation_indexes = {
        node.kind: index for index, node in enumerate(nodes) if isinstance(node, Navigation)
    }
    if not navigation_indexes:
        walk(nodes)
        return state

    required = {"segno", "dal-segno"}
    optional = {"to-coda", "coda"}
    if not required <= navigation_indexes.keys():
        raise ValueError("navigation requires segno and D.S.")
    present_optional = optional & navigation_indexes.keys()
    if present_optional and present_optional != optional:
        raise ValueError("To Coda and coda must occur together")
    if sum(isinstance(node, Navigation) for node in nodes) != len(navigation_indexes):
        raise ValueError("navigation markers must be unique")

    segno = navigation_indexes["segno"]
    dal_segno = navigation_indexes["dal-segno"]
    walk(nodes[:segno])
    tick()  # segno

    if "to-coda" in navigation_indexes:
        to_coda = navigation_indexes["to-coda"]
        coda = navigation_indexes["coda"]
        if not segno < to_coda < dal_segno < coda:
            raise ValueError("navigation markers are out of order")
        walk(nodes[segno + 1 : to_coda])
        tick()  # inert To Coda on the initial pass
        walk(nodes[to_coda + 1 : dal_segno])
        tick()  # first D.S.
        walk(nodes[segno + 1 : to_coda], replay=True)
        tick()  # active To Coda
        walk(nodes[coda + 1 :])
    else:
        if not segno < dal_segno:
            raise ValueError("navigation markers are out of order")
        walk(nodes[segno + 1 : dal_segno])
        tick()  # first D.S.
        walk(nodes[segno + 1 : dal_segno], replay=True)
        tick()  # second D.S.
        walk(nodes[dal_segno + 1 :])
    return state
