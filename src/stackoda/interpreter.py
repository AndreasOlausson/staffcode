#!/usr/bin/env python3
"""Unicode grid parser and iterative virtual machine for Stackoda."""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

# Notes are compared as NFD cells: notehead, stem and optional flag.
STEM = "\U0001D165"
MARKS = {STEM, *map(chr, range(0x1D16E, 0x1D173))}
NOTES = {"\U0001D158" + STEM: "push", "\U0001D158" + STEM + "\U0001D16E": "op", "\U0001D157" + STEM: "io"}
ACCIDENTALS = {"♯": 1, "♭": -1, "♮": 0}
CONTROLS = {
    "𝄆": "repeat",
    "𝄇": "end",
    "?": "if",
    ":": "else",
    ";": "fi",
    "𝄋": "segno",
    "𝄉": "dal-segno",
    "@": "to-coda",
    "𝄌": "coda",
    "①": "volta-1",
    "②": "volta-2",
    "③": "volta-3",
    "④": "volta-4",
}
INTEGER = re.compile(r"[ \t\n\r\v\f]*([+-]?[0-9]+)")


def cells(row: str) -> list[str]:
    result: list[str] = []
    for char in row:
        if char in MARKS:
            if not result:
                raise ValueError("combining mark without a base")
            result[-1] += char
        else:
            result.append(char)
    return result


def parse(source: str) -> list[tuple]:
    if not source:
        return []
    if not source.endswith("\n") or "\r" in source or "\t" in source:
        raise ValueError("score requires LF lines and no tabs")
    source = unicodedata.normalize("NFD", source)
    instructions = []
    for system in source[:-1].split("\n\n"):
        lines = system.split("\n")
        if len(lines) != 11 or lines[0] != "STAFF":
            raise ValueError("expected STAFF and ten rows")
        rows = [cells(row) for row in lines[1:]]
        if any(len(row) < 2 or row[0] != "|" or row[-1] != "|" for row in rows):
            raise ValueError("missing staff frame")
        if len({len(row) for row in rows}) != 1:
            raise ValueError("unequal cell widths")
        grid = [row[1:-1] for row in rows]
        background = ["-" if row % 2 else " " for row in range(10)]
        width = len(grid[0])
        consumed = set()
        occupied = set()
        for column in range(width):
            if column in occupied:
                continue
            symbols = [grid[row][column] for row in range(10)]
            if all(symbol == "|" for symbol in symbols):
                if column in occupied:
                    raise ValueError("overlapping bar")
                occupied.add(column)
                consumed.update((row, column) for row in range(10))
                instructions.append(("bar",))
                continue
            if symbols[5] == "𝄞":
                if column + 1 >= width or any(symbols[row] != background[row] for row in range(10) if row != 5):
                    raise ValueError("invalid key-signature marker")
                signature = [grid[row][column + 1] for row in range(10)]
                if any(symbol not in ACCIDENTALS and symbol != background[row] for row, symbol in enumerate(signature)):
                    raise ValueError("invalid key-signature column")
                occupied.update((column, column + 1))
                consumed.add((5, column))
                for row, symbol in enumerate(signature):
                    if symbol in ACCIDENTALS:
                        consumed.add((row, column + 1))
                offsets = tuple(ACCIDENTALS.get(signature[9 - rank], 0) for rank in range(10))
                instructions.append(("key", offsets))
                continue
            if symbols[5] in CONTROLS:
                if column in occupied or any(symbols[r] != background[r] for r in range(10) if r != 5):
                    raise ValueError("overlapping control")
                occupied.add(column)
                consumed.add((5, column))
                instructions.append((CONTROLS[symbols[5]],))
                continue
            heads = [row for row in range(10) if symbols[row] in NOTES]
            if not heads:
                continue
            family = NOTES[symbols[heads[0]]]
            if any(NOTES[symbols[row]] != family for row in heads) or (len(heads) > 1 and family != "push"):
                raise ValueError("only literal chords are supported")
            tones = []
            dots = []
            columns = {column}
            for row in heads:
                consumed.add((row, column))
                accidental = None
                if column > 0 and grid[row][column - 1] in ACCIDENTALS:
                    accidental = ACCIDENTALS[grid[row][column - 1]]
                    consumed.add((row, column - 1))
                    columns.add(column - 1)
                dotted = column + 1 < width and grid[row][column + 1] == "."
                if dotted:
                    consumed.add((row, column + 1))
                    columns.add(column + 1)
                tones.append((9 - row, accidental))
                dots.append(dotted)
            if len(set(dots)) != 1 or occupied & columns:
                raise ValueError("inconsistent dots or overlapping events")
            occupied.update(columns)
            instructions.append((family, tuple(tones), 2 if dots[0] else 1))
        for row in range(10):
            for column in range(width):
                if grid[row][column] != background[row] and (row, column) not in consumed:
                    raise ValueError("unrecognized or unattached symbol")
    return instructions


def control_links(code: list[tuple]):
    pending = []
    links = {}
    navigation = {}
    endings = {}
    ending_owner = {}
    for index, instruction in enumerate(code):
        kind = instruction[0]
        if kind in ("repeat", "if"):
            pending.append((kind, index))
        elif kind == "else":
            if not pending or pending[-1][0] != "if":
                raise ValueError("unmatched else")
            _, opener = pending.pop()
            links[opener] = index
            pending.append(("else", index))
        elif kind in ("end", "fi"):
            if not pending:
                raise ValueError("unmatched end")
            expected = ("repeat",) if kind == "end" else ("if", "else")
            previous, opener = pending.pop()
            if previous not in expected:
                raise ValueError("crossing block boundaries")
            links[opener] = index
            links[index] = opener
        elif kind.startswith("volta-"):
            if not pending or pending[-1][0] != "repeat":
                raise ValueError("volta label must be directly inside a repeat")
            opener = pending[-1][1]
            number = int(kind.removeprefix("volta-"))
            labels = endings.setdefault(opener, [])
            if number != len(labels) + 1:
                raise ValueError("volta labels must start at one and be contiguous")
            labels.append(index)
            ending_owner[index] = (opener, number)
        elif kind in ("segno", "dal-segno", "to-coda", "coda"):
            if pending:
                raise ValueError("navigation marker inside a block")
            if kind in navigation:
                raise ValueError("duplicate navigation marker")
            navigation[kind] = index
    if pending:
        raise ValueError("unclosed block")
    if navigation:
        if not {"segno", "dal-segno"} <= navigation.keys():
            raise ValueError("navigation requires segno and D.S.")
        has_to_coda = "to-coda" in navigation
        has_coda = "coda" in navigation
        if has_to_coda != has_coda:
            raise ValueError("To Coda and coda must occur together")
        order = [navigation["segno"]]
        if has_to_coda:
            order.append(navigation["to-coda"])
        order.append(navigation["dal-segno"])
        if has_coda:
            order.append(navigation["coda"])
        if order != sorted(order):
            raise ValueError("navigation markers are out of order")
    return links, navigation, endings, ending_owner


def execute(code: list[tuple], data: str = "") -> tuple[str, list[int], int]:
    links, navigation, endings, ending_owner = control_links(code)
    stack: list[int] = []
    key_offsets = [0] * 10
    offsets = [0] * 10
    output = []
    cursor = 0
    pc = 0
    loops = []
    dal_segno_fired = False
    replay = False
    while pc < len(code):
        instruction = code[pc]
        kind = instruction[0]
        if kind == "bar":
            offsets = key_offsets.copy()
        elif kind == "key":
            key_offsets = list(instruction[1])
            offsets = key_offsets.copy()
        elif kind == "repeat":
            if not replay:
                count = stack.pop() if stack else 0
                if count <= 0:
                    pc = links[pc] + 1
                    continue
                loops.append([pc, count, 1])
        elif kind == "end":
            if not replay:
                loops[-1][1] -= 1
                if loops[-1][1] > 0:
                    loops[-1][2] += 1
                    pc = loops[-1][0] + 1
                    continue
                loops.pop()
        elif kind.startswith("volta-"):
            if not replay:
                opener, number = ending_owner[pc]
                if not loops or loops[-1][0] != opener:
                    raise ValueError("volta label reached outside its repeat")
                selected = min(loops[-1][2], len(endings[opener]))
                if number < selected:
                    pc = endings[opener][selected - 1] + 1
                    continue
                if number > selected:
                    pc = links[opener]
                    continue
        elif kind == "if":
            condition = stack.pop() if stack else 0
            if not condition:
                pc = links[pc] + 1
                continue
        elif kind == "else":
            pc = links[pc] + 1
            continue
        elif kind == "fi":
            pass
        elif kind in ("segno", "coda"):
            pass
        elif kind == "to-coda":
            if replay:
                replay = False
                loops.clear()
                pc = navigation["coda"] + 1
                continue
        elif kind == "dal-segno":
            if not dal_segno_fired:
                dal_segno_fired = True
                replay = True
                loops.clear()
                pc = navigation["segno"] + 1
                continue
            if replay:
                replay = False
        else:
            _, tones, repetitions = instruction
            for rank, accidental in tones:
                if accidental is not None:
                    offsets[rank] = accidental
            value = sum(rank + offsets[rank] for rank, _ in tones)
            for _ in range(repetitions):
                if kind == "push":
                    stack.append(value)
                elif kind == "op":
                    if 0 <= value <= 4 and len(stack) >= 2:
                        a, b = stack[-2:]
                        if value >= 3 and b == 0:
                            continue
                        if value == 0:
                            result = a + b
                        elif value == 1:
                            result = a - b
                        elif value == 2:
                            result = a * b
                        elif value == 3:
                            result = a // b
                        else:
                            result = a % b
                        stack[-2:] = [result]
                    elif value == 5 and stack:
                        stack.append(stack[-1])
                    elif value == 6 and len(stack) >= 2:
                        stack[-2:] = stack[-2:][::-1]
                    elif value == 7 and stack:
                        stack.pop()
                    elif value == 8 and stack:
                        n = stack[-1]
                        if 0 <= n <= 0x10FFFF and not 0xD800 <= n <= 0xDFFF:
                            output.append(chr(stack.pop()))
                    elif value == 9 and stack:
                        output.append(str(stack.pop()))
                elif kind == "io":
                    if value in (0, 1) and len(stack) >= 2:
                        a, b = stack[-2:]
                        stack[-2:] = [int(a == b) if value == 0 else int(a > b)]
                    elif value == 2 and stack:
                        stack[-1] = int(stack[-1] == 0)
                    elif value == 3:
                        match = INTEGER.match(data, cursor)
                        if match:
                            stack.append(int(match[1]))
                            cursor = match.end()
                    elif value == 4 and cursor < len(data):
                        stack.append(ord(data[cursor]))
                        cursor += 1
        pc += 1
    return "".join(output), stack, cursor


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: stackoda PROGRAM", file=sys.stderr)
        return 2
    try:
        source = Path(sys.argv[1]).read_bytes().decode("utf-8")
        data = sys.stdin.buffer.read().decode("utf-8")
        output, _, _ = execute(parse(source), data)
        sys.stdout.buffer.write(output.encode("utf-8"))
        return 0
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
