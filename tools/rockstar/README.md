# Rockstar composer

`composer.rock` is an optional cross-esolang example. It takes one text argument
and writes a valid Stackoda score to standard output. Running that generated
score prints the original text.

Install the official [Rockstar 2](https://github.com/RockstarLang/rockstar)
engine, then run:

```bash
rockstar tools/rockstar/composer.rock "Hello from Rockstar!" \
  > /tmp/from-rockstar.staff
stackoda check /tmp/from-rockstar.staff
stackoda /tmp/from-rockstar.staff
```

The final command prints:

```text
Hello from Rockstar!
```

With no argument, the composer uses `Hello from Rockstar!` as its lyric. The
checked-in `examples/rockstar-composer.staff` file is generated from that
default.

## How it works

Rockstar iterates over the lyric and converts each character to its numeric
value. The generated Stackoda program builds that value in decimal:

1. Push the first digit.
2. For every remaining digit, push the chord `9 + 1`, multiply by ten, then add
   the digit.
3. Execute WRITE CHARACTER.

Each generated instruction occupies its own one-column staff system. This is
deliberately verbose, but keeps the composer small and makes its output easy to
inspect with `stackoda inspect`.

Rockstar stores strings as UTF-16. This first composer supports ASCII and
characters in Unicode's Basic Multilingual Plane; supplementary characters
such as most emoji are not yet combined from surrogate pairs.

Rockstar is a development-only tool for this example. The Stackoda package and
its generated score retain no Rockstar or .NET runtime dependency.
