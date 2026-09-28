# 99 Bottles

`99-bottles.staff` is the largest bundled example and a compact demonstration
of Staffcode as a real programming language rather than a text encoding.

The program:

1. Pushes `99`, duplicates it and gives one copy to `𝄆 ... 𝄇` as the fixed
   iteration count.
2. Keeps the current bottle count on the stack throughout the loop.
3. Uses `? : ;` blocks to select `bottle`, `bottles` or `no more`.
4. Decrements the retained counter once per verse.
5. Prints the final store verse after the repeat finishes.

Static ASCII is encoded as short arithmetic expressions over literal chords.
Pairs of characters are pushed in reverse order and emitted by one dotted
WRITE CHARACTER instruction, which executes twice. This reduces the source
without embedding repeated verses.

Measured against Staffcode 0.0.1:

| Property | Value |
| --- | ---: |
| Systems | 43 |
| Parsed instructions | 1,023 |
| Executed steps | 46,365 |
| Source size | 76,539 bytes |
| Output size | 11,885 bytes |

Run it with:

```bash
staffcode examples/99-bottles.staff
```

The matching `99-bottles.out` file is the executable expected result used by
the test suite.
