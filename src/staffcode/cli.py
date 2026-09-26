"""Command-line interface for the Staffcode interpreter."""

from __future__ import annotations

import sys
from pathlib import Path

from .interpreter import control_links, execute, parse


PITCHES = ("E4", "F4", "G4", "A4", "B4", "C5", "D5", "E5", "F5", "G5")


def _usage() -> str:
    return "usage: staffcode PROGRAM\n       staffcode check PROGRAM\n       staffcode inspect PROGRAM"


def _read_program(path: str) -> list[tuple]:
    source = Path(path).read_bytes().decode("utf-8")
    return parse(source)


def _format_instruction(instruction: tuple) -> str:
    kind = instruction[0]
    if kind == "key":
        offsets = ", ".join(
            f"{PITCHES[rank]}={offset:+d}"
            for rank, offset in enumerate(instruction[1])
            if offset
        )
        return f"key {offsets or '(all natural)'}"
    if kind in {"push", "op", "io"}:
        tones = ", ".join(
            f"{PITCHES[rank]}{'' if accidental is None else f'{accidental:+d}'}"
            for rank, accidental in instruction[1]
        )
        suffix = " dotted" if instruction[2] == 2 else ""
        return f"{kind} {tones}{suffix}"
    return kind


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in {"-h", "--help"}:
        print(_usage())
        return 0 if arguments else 2

    command = "run"
    if arguments[0] in {"check", "inspect"}:
        command = arguments.pop(0)
    if len(arguments) != 1:
        print(_usage(), file=sys.stderr)
        return 2

    try:
        code = _read_program(arguments[0])
        control_links(code)
        if command == "check":
            print(f"OK: {len(code)} instructions")
            return 0
        if command == "inspect":
            for index, instruction in enumerate(code):
                print(f"{index:04d}  {_format_instruction(instruction)}")
            return 0

        data = sys.stdin.buffer.read().decode("utf-8")
        output, _, _ = execute(code, data)
        sys.stdout.buffer.write(output.encode("utf-8"))
        return 0
    except (UnicodeError, ValueError, OSError) as error:
        print(error, file=sys.stderr)
        return 2
