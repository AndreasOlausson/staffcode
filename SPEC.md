# Staffcode language specification

Staffcode is a stack language written on a Unicode musical staff. These are
programming rules, not a claim to reproduce conventional musical notation.

## Running a program

Run `staffcode PROGRAM`, where PROGRAM is the path to a score. Program
input is UTF-8 on stdin. Output is UTF-8 on stdout, with no automatic separator
or newline. Normal completion exits 0. An empty program outputs nothing:
this covers both a zero-byte file and systems that contain no events.
Malformed files are outside the conformance domain. The interpreter may report
them on stderr and exit nonzero.

The stack starts empty and stores arbitrary-precision signed integers, bottom
to top. There is one input cursor, one stack and one accidental table for the
whole program. Termination occurs after the last instruction.

## The score grid

A nonempty file contains one or more systems, separated by one empty line.
Each system starts with the literal header `STAFF`, followed by ten grid rows.
The first and last cells (defined below) of every grid row are ASCII `|`. These
two frame cells are not barlines. Interior widths, counted in cells, are equal
within a system but may differ between systems. Files use UTF-8 without a BOM,
LF line endings and one final LF. No tabs occur.

Rows have the following meanings, from top to bottom:

| Row | Position | Base value | Background |
| --- | --- | --- | --- |
| 0 | G5 | 9 | space |
| 1 | F5 | 8 | `-` |
| 2 | E5 | 7 | space |
| 3 | D5 | 6 | `-` |
| 4 | C5 | 5 | space |
| 5 | B4 | 4 | `-` |
| 6 | A4 | 3 | space |
| 7 | G4 | 2 | `-` |
| 8 | F4 | 1 | space |
| 9 | E4 | 0 | `-` |

Thus there are five staff lines, four internal spaces and one space above the
staff. Labels in this table are not part of a score.

Canonically equivalent files are the same program. Before reading the grid,
apply Unicode canonical decomposition (NFD) to the whole file. Then divide each
row into cells: a cell is one code point together with every immediately
following combining stem U+1D165 or combining flag U+1D16E..U+1D172. No other
combining marks occur. Columns are cell indexes, not UTF-8 byte offsets, code
points, extended grapheme clusters or terminal display cells. Every unoccupied
cell contains its row's background character. Symbols replace that background.
Program input and output are never normalized.

Systems are concatenated in file order. Within each system, event columns are
read from left to right. Blank columns have no timing or execution effect.
A system boundary does not reset state and does not close an open block.
Systems are sequential pages, not concurrent voices.

## Notes, chords and accidentals

| Note | Cell after NFD | Precomposed spelling | Family |
| --- | --- | --- | --- |
| quarter | U+1D158 U+1D165 | `𝅘𝅥` U+1D15F | literal |
| eighth | U+1D158 U+1D165 U+1D16E | `𝅘𝅥𝅮` U+1D160 | arithmetic, stack and output |
| half | U+1D157 U+1D165 | `𝅗𝅥` U+1D15E | comparison and input |

A score may spell each note either way, and may mix spellings; both become the
same cell after NFD. These three cells are the only notes. A bare notehead
without a stem, any other combination of stem and flags, and U+1D16D COMBINING
AUGMENTATION DOT do not occur.

All notes in one column form one event. Multiple notes are allowed only for
literal chords. A chord contains at most one note on each row. An operation
event contains exactly one note. Each note may have an accidental in the cell
immediately to its left on the same row: `♯` U+266F (+1), `♭` U+266D (-1), or
`♮` U+266E (0). An ASCII `.` in the cell immediately to its right marks a
dotted event. Either all notes of a chord are dotted or none are. One dot is
permitted. An event's span is the set of columns holding its notes and their
modifiers. The spans of different events never overlap; modifiers belong only
to their adjacent notes.

Accidentals are executable state. Initially both the key-signature offset and
the active offset of every row are zero. When a note event executes, its
explicit accidentals replace the corresponding active row offsets; they do not
increment existing offsets or change the key signature. An unmarked note uses
its row's active offset. Its effective value is the base value plus that
offset. Active offsets apply to every note family. Skipped events do not change
them. A loop jump does not save or restore either offset table. Resolve a
chord's notes separately, then sum them for a single push.

A key-signature event occupies two adjacent columns. Its first column contains
`𝄞` U+1D11E MUSICAL SYMBOL G CLEF on the B4 row and background on every other
row. Its second column contains either background, `♯`, `♭` or `♮` on each row
and contains no notes or control marker. The two columns are one event. When it
executes, it replaces the entire key-signature table: sharp means +1, flat -1,
and natural or background 0. It then replaces the entire active-offset table
with that new key signature. Thus a later explicit natural sets one active row
to zero only until a barline or another key-signature event. Skipped key events
have no effect. Both columns lie in one system, and no note occurs immediately
to the right of the signature column; none of its accidentals is also a note
modifier.

A dot executes the decoded action twice consecutively. Decode once: apply
explicit accidentals once, determine the literal value or operation once,
then run that action twice. The second action sees the first action's stack
and input effects. A dotted chord pushes its sum twice, not twice its sum.
This is a Staffcode rule rather than the musical 3/2-duration convention.

## Operations

An operation's selector is its effective value, including the current
accidental. A selector absent from its family's table is a no-op. It still
applies explicit accidentals. For binary operations, pop b first and a second:
the result is a OP b. Comparisons produce integer 0 or 1.

Operand counts are fixed. ADD, SUBTRACT, MULTIPLY, FLOOR DIVIDE, MODULO, SWAP,
EQUAL and GREATER need two values. DUPLICATE, DROP, NOT, WRITE CHARACTER and
WRITE INTEGER need one. READ INTEGER and READ CHARACTER need none. NOT pops
one value and pushes 1 if it was zero, otherwise 0. Only the `?` and `𝄆`
openers substitute zero for an empty stack; operations never do.

| Selector | `𝅘𝅥𝅮` operation | `𝅗𝅥` operation |
| --- | --- | --- |
| 0 | ADD | EQUAL |
| 1 | SUBTRACT | GREATER |
| 2 | MULTIPLY | NOT (0 -> 1; any other value -> 0) |
| 3 | FLOOR DIVIDE | READ INTEGER |
| 4 | MODULO | READ CHARACTER |
| 5 | DUPLICATE top | no-op |
| 6 | SWAP top two | no-op |
| 7 | DROP top | no-op |
| 8 | WRITE CHARACTER | no-op |
| 9 | WRITE INTEGER | no-op |

FLOOR DIVIDE rounds toward negative infinity. MODULO is a - b * floor(a/b).
An action without enough operands, division/modulo by zero, or WRITE CHARACTER
with a value outside Unicode scalar values leaves the stack, input cursor and
output unchanged. Unicode scalar values are 0..0x10FFFF excluding surrogates
0xD800..0xDFFF. Explicit accidental updates still happen before such a no-op.

WRITE CHARACTER pops one scalar value and emits its UTF-8 encoding. WRITE
INTEGER pops one value and emits decimal ASCII, without whitespace; zero is
`0` and negatives have `-`. READ CHARACTER consumes one Unicode code point
(including whitespace) and pushes its scalar value; EOF is a no-op.

READ INTEGER tentatively skips ASCII space, tab, LF, CR, vertical tab and form
feed, then consumes an optional ASCII sign and the longest nonempty ASCII digit
sequence. It need not end at whitespace. Within the conformance envelope, the
digit sequence contains at most 4,096 code points including leading zeros. On
success it pushes the parsed integer and leaves the shared cursor on the code
point after the last digit. With no digits after the optional sign, the entire
read is a no-op, including the tentative whitespace skip.

## Bars and control flow

An interior column containing `|` on all ten rows is a barline. Executing it
replaces every active row offset with the corresponding current key-signature
offset. It does not change the key signature, stack or input cursor. Except for
the two-column key-signature event described above, control markers occupy only
the B4 row, with background on all other rows:

| Marker | Meaning |
| --- | --- |
| `𝄆` U+1D106 | begin counted repetition |
| `𝄇` U+1D107 | end counted repetition |
| `?` ASCII | begin conditional |
| `:` ASCII | else |
| `;` ASCII | end conditional |
| `𝄋` U+1D10B | segno label |
| `𝄉` U+1D109 | D.S. command |
| `@` ASCII | To Coda command |
| `𝄌` U+1D10C | coda label |
| `①`..`④` U+2460..U+2463 | numbered volta ending |

The body between `𝄆` and its matching `𝄇` executes max(0, count) times, and
execution then continues after that `𝄇`. The opener pops count exactly once; an
empty stack supplies zero without popping. Later changes to the stack do not
change that repetition's count. Re-entering an inner opener during an outer
iteration obtains a new inner count.

A repetition may divide the tail of its body into numbered volta endings. The
labels are direct children of that repetition, start with `①`, and increase
contiguously through at most `④`. Instructions before `①` are the common
prefix. Instructions after each label and before the next label or matching
`𝄇` are that numbered ending. On pass 1 the repetition executes the common
prefix followed only by ending `①`; pass 2 selects `②`, and so on. If there are
more passes than endings, every remaining pass selects the last ending. A
nonpositive count skips the common prefix and every ending. Skipped endings
have no effects. A nested repetition owns its own labels and starts its own
pass count at 1 each time its opener is reached. Volta labels add no execution
steps.

`?` pops a condition (zero on an empty stack). Nonzero selects the first arm;
zero selects the optional else arm. `;` ends the block. After the selected arm,
or immediately when zero selects a missing else arm, execution continues after
the matching `;`. The unselected arm is not executed, including any bars, key
events, modifiers or nested blocks inside it.

Blocks are properly nested and may cross system boundaries. Each conditional
has at most one `:` at its own nesting level. Block matching uses the full
syntactic structure even for an arm or repetition that is never executed.
End markers do not pop values.

## Segno and coda navigation

A program either contains no navigation markers, or contains exactly one segno
and one D.S. command. In the latter form it may also contain exactly one To
Coda command and one coda label; these two markers occur together or not at
all. Navigation markers occur only at the top syntactic level, outside every
repetition and conditional. Their source order is segno, optional To Coda,
D.S., optional coda.

On the initial pass, segno is a no-op and To Coda is inert. The first execution
of D.S. starts D.S. replay and jumps to the instruction immediately after
segno. Both this jump and the To Coda jump described below preserve the current
stack, input cursor, key-signature table and active accidental offsets. Neither
jump restores state from its destination's earlier execution.

While D.S. replay is active, every `𝄆`, matching `𝄇` and volta label is ignored
as a repeat mechanism: the opener does not pop a count, its entire body
executes once in source order including every numbered ending, and the end
marker does not jump. Nested repeats follow the same rule. Conditionals, notes,
key-signature events and bars retain their ordinary behavior.

If the optional coda pair exists, reaching To Coda during D.S. replay jumps to
the instruction immediately after the coda label and ends D.S. replay. The
instructions between that To Coda and the coda label are therefore not executed
on the replay pass. Without a coda pair, reaching D.S. for the second time is a
no-op that ends D.S. replay, and execution continues after it.

## Portability and resource limits

Staffcode places no semantic limit on the number of execution steps. A program
that needs more than 100,000 steps is still a valid Staffcode program.
Implementations may enforce documented resource limits, but reaching one must
be reported as an implementation error rather than as normal program output.

For portability, every conforming implementation must correctly execute
well-formed programs within this minimum profile: at most 200,000 code points
before normalization, 128 systems, 8,192 interior columns per system and blocks
nested at most 64 deep; up to and including 100,000 execution steps; a stack of
at most 4,096 items; values of at most 4,096 bits in magnitude; and input and
output of at most 64 KiB of valid UTF-8. Input contains Unicode scalar values.
Programs outside this profile remain valid, but their resource requirements may
exceed an implementation's documented limits.

For the portable profile, each half of an executed note event counts as one
step, so a dotted event counts as two. Each executed barline or key-signature
event, each executed `𝄆` or `?`, each reached navigation marker and each
completed iteration of a repetition body also counts as one step. A repeat body
executed once during D.S. replay adds no completed-iteration step. Skipped code,
blank columns, volta labels, `:`, `;` and `𝄇` add no further steps. Semantic
no-ops described above remain in the profile, even though malformed syntax does
not.
