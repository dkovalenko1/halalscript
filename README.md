# HalalScript

> *"In the name of the Compiler, the Strict, the Unforgiving of Narrowing Conversions."*

HalalScript is a small, humorous programming language whose keywords are
everyday Arabic and Islamic expressions, each chosen so that its real meaning
matches what it does in the program. The compiler speaks like a court of
scholars handing down rulings on your code: every error states the technical
fact first, then the verdict, in a tone of **pseudo-dogmatic grandiloquent
irony**. The joke is the compiler's self-importance, never the faith.

This is **stage 3** of the course project. Stage 1 gave the language a
hand-written byte state-machine lexer and a recursive-descent parser; stage 2
added functions (*dua*), structures with fields and member functions (*diwan*),
input and output (*sual* and *bayan*), a semantic pass, and LLVM IR generated
through llvmlite's builder. Stage 3 adds [loops](#loops-ma_dama-kull-and-kafa)
(`ma_dama`, `kull`, `kafa`), the ordering comparisons `<` `<=` `>` `>=`, pipes
(`x |> f`), [an optimizer](#the-optimizer) behind `--optimize`, and a
[zakat ledger](programs/zakat_ledger.txt) written in the language. The grammar
is in [`grammar.ebnf`](grammar.ebnf).

```
assalamu alaikum

wallahi dinar LIMIT := 3000000000    # compile-time constant
bismillah dirham x := 12             # immutable
inshallah dinar total := x * 2       # mutable
bismillah fatwa ok := la (total == LIMIT)

total := total + LIMIT

istikhara ok yalla
    total := total - 1
khalas
qadarallah {
    total := 0
}

ameen total
```

---

Three complete programs live in [`examples/`](examples): `tour.halal` walks
through every stage 1 feature, with experiments in its comments that trigger the
compiler's errors, `zakat.halal` is a small calculation, and `treasury.halal`
keeps a register of purses with diwans, member duas, `sual` and `bayan` (its
input is in `treasury.in`). Open them in VS Code with the
[extension](#vs-code-extension) to try the highlighting, the hovers, the live
errors and the run command.

## Running the compiler

Requirements: Python 3.10 or newer, [llvmlite](https://llvmlite.readthedocs.io)
0.49 (in `requirements.txt`), and the [LLVM](https://llvm.org) tools on `PATH`
to run the result: `lli`, or `llc` and `clang`.

```sh
git clone https://github.com/dkovalenko1/halalscript.git
cd halalscript
git checkout stage3
python3 -m venv .venv
# activate the environment as your shell requires, e.g. source .venv/bin/activate
pip install -r requirements.txt

python compiler.py examples/tour.halal output.ll   # compile to LLVM IR
lli output.ll                                      # run it
llc -filetype=obj output.ll -o output.o            # or build it into a program
clang output.o -o program

python compiler.py --ast examples/tour.halal       # print the syntax tree
python compiler.py --tokens examples/tour.halal    # print the tokens (debugging)
python compiler.py examples/tour.halal             # only check the program
python compiler.py --optimize examples/tour.halal output.ll   # optimize, then compile
python compiler.py --optimize --ast examples/tour.halal       # the tree after the optimizer
```

`--ast`, `--tokens` and the check without an output file do not need llvmlite.

A compiled program prints what its `bayan` statements proclaim, then its
answer: `Program exit with result 25`. On a runtime overflow it prints the
*riba* verdict instead and exits with code 1.

On an error the compiler prints exactly one line to stderr, prints nothing to
stdout, writes no output file, and exits with code 1:

```
compilation error: line 3:17: 'yalla' is never answered by 'khalas' — a journey begun was not concluded
```

## The program: a zakat ledger

[`programs/zakat_ledger.txt`](programs/zakat_ledger.txt) asks for your savings
one amount per line, until you enter 0, and refuses a negative amount with a
message. Then it prints how many amounts it recorded, their total, and the
zakat due on them: nothing below the nisab of 200, one fortieth from it up.
The amounts go into a `Purse` diwan through its member dua `add`. A `ma_dama`
loop asks for the next amount until it reads 0, and the dua `share` divides
with a second `ma_dama` loop, since the language has no `/`. The zakat is one
pipe: `purse.total |> zakatable |> share(1, 40)`. To build it into a native
program and run the two recorded sessions:

```sh
python compiler.py programs/zakat_ledger.txt zakat_ledger.ll
llc -filetype=obj zakat_ledger.ll -o zakat_ledger.o
clang zakat_ledger.o -o zakat_ledger
./zakat_ledger < programs/zakat_ledger.due.in        # prints programs/zakat_ledger.due.expected
./zakat_ledger < programs/zakat_ledger.exempt.in     # prints programs/zakat_ledger.exempt.expected
```

Build it on the machine that runs it: the `.ll` file names the target of the
machine that compiled it. `./zakat_ledger` alone asks for the amounts on the
terminal. `check.py` runs both sessions under `lli`.

## VS Code extension

[`vscode-halalscript/`](vscode-halalscript/README.md) adds HalalScript support to
VS Code for `.halal` files: highlighting, the compiler's syntax and semantic
errors underlined as you type, keyword rulings and signatures on hover,
completion (after `t.purse.`, the fields and member duas of that diwan),
snippets, `yalla`/`khalas` bracket matching, Eastern Arabic digit conversion, a
syntax-tree viewer, and a command that runs the program in a terminal. It knows
the stage 2 language: its bundled compiler does not accept loops or pipes yet.

```sh
cd vscode-halalscript && npm install && npm run package
code --install-extension halalscript-0.2.0.vsix
```

## Running the tests

```sh
python check.py                  # set LLI=/path/to/lli if lli is not on PATH
python check.py --optimize       # the same suite, every program compiled with --optimize
```

`check.py` compiles every program in `tests/ok` to `.ll`, runs it under `lli`,
and compares everything it prints with the `.expected` file next to it; when
`NAME.in` exists, it is the program's standard input (the input is not echoed,
so `.expected` holds only what the program prints). A program with a `.ast`
file must also print exactly that tree with `--ast`. Every program in
`tests/err` must be rejected with stderr equal to its `.expected` file, nothing
on stdout and no output file. Every program in `examples/` must compile and
run. Every program in `tests/opt` must print its `.ast` file with
`--optimize --ast`, and its `.expected` output both with and without
`--optimize`. Each recorded session of a program in `programs/`
(`NAME.SESSION.in`) must print exactly `NAME.SESSION.expected`. It prints a
PASS/FAIL table, lists the failed tests, and exits non-zero if any test fails.
There are 47 valid, 109 invalid and 7 optimizer programs, each named after what
it covers. With `--optimize`, `check.py` compiles every test that way and skips
the `.ast` files of `tests/ok`, which hold the tree before the optimizer.

---

## The language

### Program structure and the greeting

*"Peace be upon you."* Every program opens with
`assalamu alaikum` on its first line and ends with `ameen <value>`. One
statement per line; blank lines and `#` comments may stand anywhere. Between
the two, the order is fixed: first the diwans, then the duas, then the
statements.

> **Official Ruling.** A program that enters without greeting is turned away
> at the door. A lone `assalamu` is a greeting abandoned halfway, which is
> considered worse than none.

```
assalamu alaikum   # peace be upon you
ameen 0
```

### `ameen` — the program's answer (exit)

*"So be it", said at the end of a supplication.* `ameen <expr>` is the
last statement of the program; it may also be the last statement of a block.
At the top level it ends the program, whose answer is a dirham, a dinar or a
fatwa; inside a *dua* it ends the dua, and its value is the dua's answer.

> **Official Ruling.** Every program is a supplication and every supplication
> ends with *ameen*. Nothing may be spoken after it — not in its block, not in
> the program.

```
assalamu alaikum
bismillah fatwa answer := haram
ameen answer != halal
```

### Declarations — the three degrees of certainty

`<kind> <type> <name> := <expr>`. The type and the initialiser are mandatory.

#### `wallahi` — compile-time constant

*"By God, I swear" — the oath that settles a matter beyond dispute.*

> **Official Ruling.** A *wallahi* value is sworn before the program is born.
> An oath is not taken on what one will discover later, so its initialiser may
> name only literals and other *wallahi* values. To reassign it would be to
> break an oath, and the compiler, which keeps careful records, will not let the
> programmer become a perjurer.

#### `bismillah` — immutable variable

*"In the name of God" — said at the beginning of an act.*

> **Official Ruling.** Declaration is the act of naming, and there is no more
> solemn naming than one opened with *bismillah*. The value may be computed at
> runtime, but once begun in the Name it is not revisited.

#### `inshallah` — mutable variable

*"If God wills" — said of any future that is not certain.*

> **Official Ruling.** A value declared *inshallah* is held only
> provisionally. It shall remain what it is — if God wills. He may will
> otherwise, and `:=` is how that will is expressed.

```
assalamu alaikum
wallahi dirham NISAB := 85
bismillah dirham wealth := NISAB * 3
inshallah dinar savings := wealth
ameen savings
```

### Types — the treasury

| HalalScript | Meaning | Equivalent |
|-------------|---------|------------|
| `dirham` | the silver coin | `i32` |
| `dinar`  | the gold coin   | `i64` |
| `fatwa`  | a scholar's ruling on what is permitted | `bool` |
| `halal` / `haram` | permitted / forbidden | `true` / `false` |

> **Official Ruling on the Coinage.** As gold exceeds silver, so does the
> dinar exceed the dirham. A dirham may always be placed in a purse of dinars;
> a dinar may never be pressed into a dirham's purse, for what spills over is
> *riba* — unlawful increase. Every *fatwa* resolves to *halal* or *haram*;
> those who want a third verdict are referred to a looser type system.

```
assalamu alaikum
bismillah dirham small := 7
bismillah dinar big := 3000000000
bismillah fatwa ruling := halal
ameen small
```

### Assignment — `:=`

`<name> := <expr>`, or `<name>.<field> ... := <expr>` for a field. Only an
`inshallah` variable may be assigned, and a field only through a chain that is
`inshallah` at every link.

> **Official Ruling.** `:=` is *tawba*, repentance: the variable turns away from
> its former value toward a new one. The *bismillah* and the *wallahi* have
> nothing to repent of.

```
assalamu alaikum
inshallah dirham a := 10
a := a * 2 - 1
ameen a
```

### Expressions and operators

| Operator | Meaning |
|----------|---------|
| `+ - *` | arithmetic; `*` binds tighter, equal levels group left to right |
| `==` `!=` | comparison; at most one per expression, weaker than arithmetic |
| `<` `<=` `>` `>=` | ordering of dirhams and dinars, at the level of `==` |
| `\|>` | pipe: `x \|> f` is `f(x)`; binds loosest of all |
| `la` | logical not (*la*, "no"); binds tightest: `la a == b` is `(la a) == b` |
| `( )` | grouping |

There is no unary minus (write `0 - x`) and no `/`.

> **Official Ruling on Equality.** Equality is established by two witnesses,
> `==`; a single `=` is one witness, and one witness establishes nothing.
> **On Negation.** The `!` is an exclamation, not an argument; negation is
> spoken plainly: *la*.

```
assalamu alaikum
bismillah dirham x := (2 + 3) * 4
bismillah fatwa different := x * 2 != x + 5
bismillah fatwa refused := la (x == 20)
ameen different
```

### `istikhara` / `qadarallah` — if / else

*Istikhara* is the prayer for guidance before a decision; *qadarallah*, "God
has decreed it", is what one says when things did not go as hoped. The block
opener ends the header line; the closer stands alone on its line; `qadarallah`
starts the line after the closer. Each block holds at least one statement;
blocks nest; `qadarallah` is optional.

> **Official Ruling.** Before a branch is taken, guidance is sought. When the
> *istikhara* returns *haram*, the programmer does not despair: they say
> *qadarallah* and walk the other path. A *qadarallah* with no *istikhara* is
> rejected — one cannot accept a decree that was never sought.

```
assalamu alaikum
inshallah dirham r := 0
istikhara r == 0 yalla
    r := 1
khalas
qadarallah yalla
    r := 2
khalas
ameen r
```

### Blocks — `yalla … khalas` or `{ … }`

*Yalla*, "come on, let's go"; *khalas*, "enough, it's finished". Braces are an
equivalent second style. A block must be closed in the style it was opened in;
the then-block and the else-block may differ.

> **Official Ruling.** A block is entered with eagerness and left with
> finality. For those who arrive from the lands of C, braces are tolerated in
> the spirit of facilitation. But a block is a covenant, closed in the tongue in
> which it was opened: a *yalla* answered by `}` is a broken covenant.

```
assalamu alaikum
inshallah dirham a := 10
istikhara a == 10 {
    a := a + 5
}
qadarallah yalla
    a := a - 5
khalas
ameen a
```

### Loops: `ma_dama`, `kull` and `kafa`

*Ma dama*, "as long as": `ma_dama <fatwa> yalla ... khalas` runs its block again
and again while the fatwa holds, checking it before every round. *Kull*,
"each": `kull dirham i := 1 ila n yalla ... khalas` runs its block once for
each `i` from `1` to `n` (*ila*, "up to"), both included. *Kafa*, "enough",
leaves the innermost loop.

The rules:

- The condition of `ma_dama` is a fatwa.
- The counter of `kull` is a dirham or a dinar, and both bounds must fit its
  type. Both bounds are computed once, before the first round, so changing a
  variable that a bound reads does not change the number of rounds. A range
  whose last value is below its first runs no round.
- The counter is declared by the loop: it lives in the block only, it cannot
  be assigned, and the block cannot declare a second variable of its name.
- The counter never overflows. The loop stops when the counter reaches the
  last value, before adding 1, so `kull dirham i := 1 ila 2147483647` is legal.
- A block of a loop may declare variables; each round initialises them again.
- `kafa` stands only inside a loop, and is the last statement of its block. A
  `kafa` in a dua body leaves a loop of that dua, never a loop around the call.
- `ameen` inside a loop leaves the dua (or ends the program) at once.

> **Official Ruling.** *Kull* counts what it was told to count, and no one else
> touches the count. One who must stop early says *kafa*, and the loop yields;
> but *kafa* said outside a loop is a word thrown into the wind.

```
assalamu alaikum
# The smallest n whose square is above a limit read from the user.
bismillah dirham limit := sual()
inshallah dirham n := 1
ma_dama n * n <= limit yalla
    n := n + 1
khalas
ameen n
```

```
assalamu alaikum
# A multiplication table without its diagonal, and only up to 3 x 3.
kull dirham row := 1 ila 9 yalla
    istikhara row > 3 yalla
        kafa
    khalas
    kull dirham column := 1 ila 3 yalla
        istikhara row != column yalla
            bismillah dirham product := row * column
            bayan(product)
        khalas
    khalas
khalas
ameen 0
```

**The IR of a `kull` loop.** The excerpt is `output.ll` for
`kull dirham i := 1 ila 10 yalla sum := sum + i khalas`, without the overflow
check of `+` inside the body:

```llvm
  store i32 1, i32* %"i"
  br label %"for.cond"
for.cond:
  %".5" = load i32, i32* %"i"
  %".6" = icmp sle i32 %".5", 10
  br i1 %".6", label %"for.body", label %"for.end"
  ...                                  ; for.body adds i to sum, then: br label %"for.step"
for.step:
  %".21" = load i32, i32* %"i"
  %".22" = icmp eq i32 %".21", 10
  br i1 %".22", label %"for.end", label %"for.next"
for.next:
  %".24" = add nsw i32 %".21", 1
  store i32 %".24", i32* %"i"
  br label %"for.cond"
```

The counter lives in an `alloca` from the entry block, and the store before
`for.cond` gives it the first value; both bounds were computed there, once.
`for.cond` compares the counter with the last value and enters `for.body` or
jumps past the loop to `for.end`; `kafa` is a `br` to `for.end` as well.
`for.step` leaves when the counter has reached the last value, so `for.next`
adds 1 only when the result fits, and its `br label %"for.cond"` is the back
edge that makes the loop. A `ma_dama` loop has the same shape with three
blocks: `while.cond`, `while.body`, whose last `br` back to `while.cond` is the
back edge, and `while.end`.

### Pipes: `|>`

`x |> f` calls the dua `f` with `x`, and `x |> f |> g(a)` is `g(f(x), a)`: each
stage is a global dua, called with the value of the stages before it as its
first argument and the arguments in its brackets after that. A pipe reads in
the order things happen, where nested calls read inside out.

The rules:

- A stage is the name of a dua, with or without brackets. A diwan, a variable
  or a chain such as `c.add` cannot be a stage. Inside a member dua, a stage
  named like a member dua of the same diwan calls it on the object, as a plain
  call there would.
- `|>` binds loosest of all: `2 + 3 |> f` pipes 5, and a comparison of a pipe
  needs brackets, `(x |> f) == 3`.
- The stages run left to right. The value is computed first, then the stage
  that takes it, then the next one; a stage's own arguments come after its
  piped value.
- The type of each stage's answer is checked against the first parameter of
  the next stage, with the usual widening of a dirham into a dinar. An error
  names the stage that does not fit, counted from 1, and the stage before it:
  `pipe stage 3 'double' does not fit: it takes dirham as 'x', but stage 2 'big'
  answers with fatwa`. A wrong number of arguments or an unknown dua names its
  stage too.
- A pipe stands wherever a value does: in a declaration, an assignment, a
  condition, `bayan`, `ameen` and the arguments of a call.

> **Official Ruling.** A value is handed from one supplication to the next, as
> a petition passes from clerk to clerk. Each clerk accepts only the coin he
> asked for; a petition that does not fit is returned with the name of the
> clerk who refused it.

```
assalamu alaikum
dua dirham add(dirham x, dirham y) yalla
    ameen x + y
khalas
dua dirham double(dirham x) yalla
    ameen x * 2
khalas
# double(add(sual(), 3)), read left to right
ameen sual() |> add(3) |> double
```

```
assalamu alaikum
diwan Point yalla
    bismillah dirham x
    bismillah dirham y
khalas
dua Point mirror(Point p) yalla
    ameen Point(p.y, p.x)
khalas
dua fatwa on_axis(Point p) yalla
    ameen p.x == 0
khalas
# An object flows through a pipe like any value.
istikhara Point(0, 5) |> mirror |> on_axis yalla
    bayan("on the axis")
khalas
qadarallah yalla
    bayan("off the axis")
khalas
ameen 0
```

The parser turns a pipe into calls: each stage is a `Call` with its stage
number, so the semantic pass, the optimizer and the code generator see an
ordinary call, and only the error messages speak of stages. In `--ast`:

```
Decl zakat dinar bismillah (immutable)
  Call share (3 arguments, pipe stage 2)
    Call zakatable (1 argument, pipe stage 1)
      Field purse.total
    Int 1
    Int 40
```

**The IR of a pipe.** The excerpt is `output.ll` for the zakat line of
[the program](#the-program-a-zakat-ledger),
`bismillah dinar zakat := purse.total |> zakatable |> share(1, 40)`:

```llvm
  %".110" = getelementptr inbounds %"Purse", %"Purse"* %"purse", i32 0, i32 0
  %".111" = load i64, i64* %".110"
  %".112" = call i64 @"hs.zakatable"(i64 %".111")
  %".113" = call i64 @"hs.share"(i64 %".112", i32 1, i32 40)
  store i64 %".113", i64* %"zakat"
```

The `getelementptr` reaches field 0 of the object `purse`, its `total`, and
the `load` reads the value the pipe starts from. Each stage is one `call`, in
the order of the stages, and the register one call returns is the first
argument of the next: `%".112"`, the answer of `zakatable`, goes into `share`
before its own arguments 1 and 40. The last answer is stored in the slot of
`zakat`; there is no trace of the pipe left in the IR, only two calls.

### Eastern Arabic numerals

Integer literals may be written in Western digits `0-9` or in Eastern Arabic
digits (U+0660 for zero to U+0669 for nine), but one literal uses one script.
The lexer reads each Eastern Arabic digit as a two-byte UTF-8 sequence in its
state machine; the AST shows both the value and the source spelling. The
examples are in [`tests/ok/arabic_numerals.txt`](tests/ok/arabic_numerals.txt)
(they are left out of this README because right-to-left digits garble the
Markdown preview).

### Overflow — *riba*

*Riba* is unlawful increase; in HalalScript it is the name of every overflow.
It is checked at four points:

- the lexer rejects a literal larger than the largest dinar (9223372036854775807);
- the semantic pass rejects a literal that does not fit a dirham where a
  dirham is expected, and any dinar → dirham narrowing;
- `wallahi` constants are folded at compile time, and an overflow while folding
  is a compilation error;
- `+ - *` are computed through `llvm.sadd/ssub/smul.with.overflow`, and
  `sual()` checks that the number it read fits a dirham; when one overflows at
  runtime, the program prints the verdict and exits with code 1.

```
compilation error: line 2:22: constant 9223372036854775808 exceeds even the dinar (i64) — this is riba, an increase beyond every permitted measure
riba: dirham overflow in '+' at line 4:8 — the value increased beyond its permitted measure; execution is halted in disapproval
```

### `dua` — functions

*Du'a, "supplication": a request that is answered.* A dua names the coin of
its answer, its name, and what it is given; its block ends with `ameen`, whose
value is the answer. A call is an expression: `add(1, add(2, 3))`.

> **Official Ruling.** Every program is a supplication, and a *dua* is a
> smaller one within it: it asks, and *ameen* gives its answer. A dua is offered
> with exactly what it asks, no more and no less, and it is answered in the coin
> it asked for. It carries only what is handed to it: the variables of the
> program stay outside, for one does not bring the whole household into a
> private prayer.

```
assalamu alaikum
dua dirham fib(dirham n) yalla
    istikhara n == 0 yalla
        ameen 0
    khalas
    istikhara n == 1 {
        ameen 1
    }
    ameen fib(n - 1) + fib(n - 2)
khalas
ameen fib(10)
```

### `diwan` — structures

*The diwan was the register of the early caliphate, which recorded each person
and their entries.* A diwan lists its fields, each `bismillah` (fixed when the
object is created) or `inshallah` (mutable), then its member duas. An object is
created with one value per field, in order: `Point(3, 4)`. A field is read
through a chain, `c.center.x`.

> **Official Ruling.** A register is drawn up before the business begins: the
> diwans come first in the program, and in each diwan the entries are written
> before the duties. An entry begun with *bismillah* is set when the object is
> created and never amended; an *inshallah* entry may be, but only by one whose
> every link to it is *inshallah* too, for a chain is as amendable as its
> stiffest link.

```
assalamu alaikum
diwan Point yalla
    inshallah dirham x
    inshallah dirham y
khalas
diwan Circle {
    inshallah Point center
    bismillah dirham radius
}
inshallah Circle c := Circle(Point(3, 4), 2)
c.center.x := 10
ameen c.center.x + c.radius
```

### Member duas

A dua declared inside a diwan is called on an object: `p.shift(2)`,
`c.center.d2()`. Inside it, the fields of the object are visible by name.

> **Official Ruling.** Duties are performed by an object, never by its register:
> `Point.d2()` is rejected. A duty that amends its object, directly or through
> another duty, may be laid only on an object that may be amended.

```
assalamu alaikum
diwan Point yalla
    inshallah dirham x
    inshallah dirham y
    dua dirham shift(dirham dx) yalla
        x := x + dx
        ameen x
    khalas
khalas
inshallah Point p := Point(3, 4)
bismillah dirham moved := p.shift(2)
ameen p.x
```

### `sual` and `bayan` — input and output

*Su'al*, "question"; *bayan*, "proclamation". `sual()` reads one dirham from
the standard input: the next number, wherever it stands, so `3 4` on one line
and `3` and `4` on two lines are the same answer to two calls. When the input
holds no number there (a word, or nothing left), or a number that does not fit
a dirham, the program prints the verdict and exits with code 1 before the
value is used. `bayan(...)` prints one value, or one string literal, and a
newline.

> **Official Ruling.** The program puts its question to the user and receives
> the answer as a dirham. An answer that is not a coin, or a coin too large for
> the purse, is not accepted in place of one. It proclaims one thing at a time, for the herald has
> one voice. A string literal is a proclamation and nothing else: it cannot be
> stored, added or answered.

```
assalamu alaikum
bismillah dirham a := sual()
bayan("you said:")
bayan(a)
bayan(a == 7)
ameen a
```

With `7` on the standard input it prints `you said:`, `7`, `halal`, then
`Program exit with result 7`.

### The rules the semantic pass enforces

A separate pass over the tree checks these rules before any IR is built. Each
is covered by a program that follows it (`tests/ok`) and one that breaks it
(`tests/err`).

**Types.** A literal is a dirham if it fits one, otherwise a dinar. `+ - *` take
two integers and give the wider coin; `==` and `!=` take two integers of any
width, or two fatwas, and give a fatwa; `la` and the condition of `istikhara`
take a fatwa. A dirham widens into a dinar wherever a dinar is expected;
nothing else converts. A literal that does not fit a dirham where a dirham is
expected is riba.

**Declarations.** A name is declared before its use and once per block. Each
block is a scope, and an inner declaration may shadow an outer one with any
type. Only `inshallah` may be assigned. A `wallahi` initialiser names only
literals and other `wallahi` constants, and it is folded at compile time. A
variable, a parameter or a dua cannot take the name of a diwan or of a dua.

**Arguments and answers.** A call gives exactly as many arguments as the dua
has parameters, each of the parameter's type (a dirham may go into a dinar
parameter). The value after `ameen` in a dua has the dua's result type (a
dirham may answer for a dinar). A call has the result type of its dua.
Parameters are copies and cannot be assigned. A dua may call itself and any dua
declared below it.

**What a dua body sees.** Its parameters, its own locals, and every dua of the
program; a member dua also sees the fields of its object. It never sees the
top-level variables, not even the `wallahi` constants. Parameters and the
locals of the body's own block share one scope, so a local cannot take a
parameter's name; an inner block may shadow it.

**Name lookup inside a member dua.** A name is looked up among the parameters
and locals first, then among the fields of the diwan; a parameter or local
named like a field hides the field. A top-level variable is never reached: when
a parameter, a field and a top-level variable share a name, the parameter wins,
and a name found only at the top level is an error. A call `f(...)` is looked up among the member duas of
the same diwan first, then among the global duas, so a member dua hides a
global dua of the same name; `f()` inside `Point` calls `f` on the same object.

**Diwans.** A field's type is a coin, a fatwa or a diwan declared above; a
diwan cannot contain itself and has at least one field. Fields come before
member duas; a field and a member dua, or two member duas, cannot share a name.
An object is created with one value per field, in order, each of the field's
type. A field is read through a chain whose every link exists.

**Mutability of chains.** An assignment through `c.center.x` needs every link
to be `inshallah`: the variable `c`, the field `center` and the field `x`.
Replacing a whole object, `c := ...`, needs every field at every depth to be
`inshallah`.

**Mutating member duas.** A member dua is mutating if it assigns a field of its
object, or calls a mutating member dua on its object or on one of its fields.
Member duas may call each other in a cycle, so the marks are settled after all
bodies are checked: the duas that assign a field are marked, then the marks
spread until none is added. A mutating dua may be called only through a chain
that is `inshallah` at every link; a parameter is never amendable. A
non-mutating dua may be called on anything.

**How an object is printed.** Its diwan's name, then each field as
`name: value` in declaration order, separated by `, `, in parentheses, the way
the object is created: `Circle(center: Point(x: 3, y: 4), radius: 2)`. A field
that is an object is printed the same way.

**Where `bayan` puts a newline.** After every value it prints, and nowhere
else. A string literal is printed exactly as written: there are no escape
sequences, so `\n` inside it is two characters, and `%` stays `%`. All output of
`bayan` comes before the `Program exit with result` line.

**Fatwas are printed as `halal` and `haram`.** The stage asked for booleans to
be printed as `true` and `false`, not as numbers. HalalScript prints its own
words for them, because `halal` and `haram` are the language's boolean
literals; the exit line of a fatwa answer uses them too.

| Rule | Followed in `tests/ok` | Broken in `tests/err` |
|------|------------------------|-----------------------|
| argument count and types | `fn_two_args_widen`, `fn_nested_calls_no_args` | `call_too_many_arguments`, `call_too_few_arguments`, `call_argument_wrong_type`, `call_argument_narrowing` |
| the type of an answer | `fn_answer_widens`, `dua_object_param_and_result` | `dua_wrong_answer_type`, `program_answers_object` |
| what a dua body sees | `fn_recursion_and_forward` | `dua_sees_no_top_level`, `dua_sees_no_wallahi`, `param_assigned` |
| name lookup in a member dua | `member_name_shadowing`, `member_lookup_order`, `member_call_on_field_named_like_diwan` | `member_sees_no_top_level` |
| fields, objects, chains | `new_nested_and_copy`, `field_chain_write` | `unknown_field`, `new_wrong_value_count`, `new_field_wrong_type`, `field_declared_twice`, `diwan_contains_itself` |
| mutability of chains | `field_chain_write` | `assign_through_constant_object`, `assign_through_constant_field`, `assign_object_with_constant_field`, `assign_constant_field_in_member` |
| mutating member duas | `member_mutating_cycle`, `member_mutates_through_field`, `member_local_not_mutating`, `field_chain_write` | `mutating_call_on_constant_object`, `mutating_call_through_constant_field`, `mutating_call_on_constant_field_in_member`, `mutating_cycle_on_constant_object`, `mutating_call_on_parameter` |
| member calls | `field_chain_write`, `member_lookup_order` | `member_dua_unknown`, `member_call_on_coin`, `member_call_on_diwan` |
| printing and reading | `print_every_kind`, `bayan_nul_byte`, `read_input`, `read_not_a_number` | `bayan_as_value`, `bayan_two_values`, `bayan_empty`, `string_outside_bayan`, `sual_with_argument` |
| program and diwan order | every program with a diwan | `dua_after_statement`, `diwan_after_dua`, `dua_inside_dua`, `field_after_member_dua`, `member_dua_before_field` |
| types and declarations (stage 1 rules) | `scope_shadowing`, `decl_all_kinds`, `long_expression` | `undeclared_name`, `redeclared_in_block`, `variable_named_like_dua`, `member_dua_named_like_diwan`, `assign_bismillah`, `assign_wallahi`, `narrowing_dinar_to_dirham`, `compare_fatwa_with_dirham`, `arithmetic_on_fatwa`, `condition_not_fatwa`, `la_on_dirham` |
| loops | `loop_nested_kafa`, `loop_range_edges`, `loop_ameen_inside` | `loop_kafa_outside`, `loop_assign_counter`, `loop_counter_after_loop`, `loop_statement_after_kafa`, `loop_condition_not_fatwa` |
| pipes | `pipe_chain_arguments`, `pipe_order_and_places`, `pipe_member_stage` | `pipe_stage_wrong_type`, `pipe_source_wrong_type`, `pipe_stage_argument_count`, `pipe_into_member_chain`, `pipe_unknown_stage` |
| riba | `wallahi_folding`, `runtime_riba`, `read_beyond_dirham`, `literal_i64_max` | `wallahi_fold_overflow`, `wallahi_runtime_value`, `literal_too_big_for_dirham`, `literal_beyond_i64` |

### Names and reserved words

Names are ASCII letters, digits and `_`, not starting with a digit. Reserved:
`wallahi bismillah inshallah dirham dinar fatwa halal haram istikhara
qadarallah yalla khalas ameen la assalamu alaikum ma_dama kull ila kafa diwan
dua sual bayan`. Keywords are lowercase, so `Bismillah` is an ordinary name.

---

## The syntax tree

`--ast` prints one node per line, indented two spaces per level, with every
flag and field:

```
Program
  Decl x dirham bismillah (immutable)
    Int 12
  Istikhara
    BinOp ==
      Var x
      Int 12
    Block yalla
      Ameen
        Int 1
    Qadarallah
      Block brace
        Ameen
          Int 2
  Ameen
    Int 0
```

A literal written in Eastern Arabic digits also shows its source spelling in
parentheses after the value. The stage 2 nodes show their types and flags:

```
Program
  Diwan Point yalla
    Field x dirham inshallah (mutable)
    Field y dirham bismillah (immutable)
    Dua shift(dirham dx) -> dirham (member of Point)
      Param dx dirham (immutable)
      Block yalla
        ...
  Dua area(Point p) -> dinar
    Param p Point (immutable)
    Block yalla
      ...
  Decl p Point inshallah (mutable)
    New Point (2 values)
      Sual
      Int 4
  Bayan
    MemberCall shift on p (1 argument)
      Int 2
  Bayan
    String "done"
  Ameen
    Call area (1 argument)
      Field p.x
```

The loops print as `MaDama` (its condition, then its block), `Kull i dirham`
(the first value, the last value, then the block) and `Kafa`.

A stage of a pipe prints as a `Call` with its number: `Call share (3
arguments, pipe stage 2)`.

`Field p.x` is a field chain; `MemberCall ... on c.center` is a chain that ends
in a member call; `Call` is a call of a global dua, or of a member dua of the
same diwan from inside it.

Node classes (`src/ast_nodes.py`): `ASTNode` → `ProgramNode`, `BlockNode`,
`DiwanNode`, `FieldDeclNode`, `DuaNode`, `ParamNode`, `StmtNode` (`DeclNode`,
`AssignNode`, `IfNode`, `WhileNode`, `ForNode`, `BreakNode`, `ExitNode`,
`PrintNode`) and `ExprNode` (`BinOpNode`,
`NotNode`, `IntLiteralNode`, `BoolLiteralNode`, `VarNode`, `FieldAccessNode`,
`CallNode`, `MemberCallNode`, `NewNode`, `ReadNode`, `StringNode`). Every node
keeps the line and column of the token it came from.

## How the compiler is built

| File | Phase |
|------|-------|
| `src/lexer.py` | byte state machine → one token vector per line |
| `src/parser.py` | recursive descent, one method per grammar rule → AST |
| `src/semantic.py` | symbol tables for variables, duas and diwans; every check above |
| `src/optimizer.py` | with `--optimize`: removes unused variables and duas, inlines duas called once |
| `src/codegen.py` | LLVM IR through llvmlite's `IRBuilder`; the only IR text is `str(module)` |
| `compiler.py` | the command line; writes `output.ll` only when every phase succeeded |

In the IR, each diwan is an identified struct type (`%"Point" = type {i32, i32}`)
and an object is an `alloca` of it; a field is a `gep` by the index the semantic
pass found. Each dua is a function named `hs.<name>`, and each member dua a
function `hs.<Diwan>.<name>` whose first parameter is a pointer to the object;
a call passes the object's address, so a mutating dua changes the original.
The `hs.` prefix keeps a dua called `main` or `printf` apart from the runtime.
Every function is declared before any body is built. `printf`, `scanf` and
`exit` are declared from the C library; the format strings are global
constants; printing an object walks the diwan's field table with one `gep`,
`load` and `printf` per field.

## The optimizer

`--optimize` runs three transformations of the checked tree before code
generation, and repeats them until none of them changes anything. The semantic
pass has already pointed every name at its declaration and every call at its
dua, so the optimizer compares objects, not names: two variables named `x` in
different scopes are different variables, and shadowing needs no special care.

**Unused variables.** A declaration that nobody reads is removed together with
every assignment to it, again and again, so a variable read only by another
removed variable goes next. A declaration stays if its value, or the value of
any assignment to it, calls a dua, calls `sual()` or computes `+`, `-` or `*`.
A call may print or read, and arithmetic may halt the program on riba, which
the program's output shows; the language has no statement that would keep the
computation without the variable. A `wallahi` value is the exception: the
semantic pass computed it, and checked it for riba, at compile time. Parameters
and the counter of `kull` are never removed. Counting has one limit: a variable
that only feeds itself, `rounds := rounds + i`, is read by its own assignment,
so it stays.

**Unused duas.** The optimizer walks the calls from the top-level statements
to the duas they call, and on to the duas those call. Every dua it does not
reach is removed with its body, member duas included. One walk finds duas that
call only each other, or only themselves.

**Inlining.** A global dua called exactly once is replaced at its call site:

- each parameter becomes `bismillah <type> f.<param> := <argument>`, so an
  argument is computed once even when the body reads it twice;
- the statements of the body follow, every local renamed `f.<name>`;
- `bismillah <type> f.ameen := <value of the ameen>` holds the answer, and the
  call is replaced by the variable `f.ameen`;
- then the dua has no call left, and the next round removes it.

A `.` cannot stand in a source name, so the new names cannot collide with the
caller's, and `ameen` is a reserved word, so `f.ameen` cannot collide with a
renamed local of `f`. These statements go in front of the statement that held
the call, which then reads `f.ameen`. The inliner leaves these shapes alone:

- a member dua, because its body works on the fields of an object;
- a recursive dua: its own call counts, so it is never called exactly once;
- a body that leaves through an `ameen` inside a block, for example inside an
  `istikhara`: moved into the caller, that `ameen` would end the caller;
- a call in the condition of `ma_dama`, which is computed on every round;
- a call computed after a call, a `sual()` or an arithmetic operation of the
  same statement: moving the body in front would run it first. In
  `bayan(loud(1) + quiet(2))`, `quiet` stays a call unless `loud` was inlined
  first.

The tests are in `tests/opt`, two or more per transformation:

| Transformation | Tests |
|----------------|-------|
| unused variables | `opt_unused_var_chain`, `opt_unused_var_effects` |
| unused duas | `opt_unused_dua_chain`, `opt_unused_dua_recursive` |
| inlining | `opt_inline_basic`, `opt_inline_positions`, `opt_inline_left_alone` |

**Inlining in the IR.** For this program:

```
assalamu alaikum
dua dirham square(dirham x) yalla
    ameen x * x
khalas
bismillah dirham n := sual()
ameen square(n + 1)
```

Without `--optimize`, `main` computes `n + 1` and calls the dua, which has a
function of its own:

```llvm
define i32 @"hs.square"(i32 %"x")
{
entry:
  %"x.1" = alloca i32
  store i32 %"x", i32* %"x.1"
  %".4" = load i32, i32* %"x.1"
  %".5" = load i32, i32* %"x.1"
  %".6" = call {i32, i1} @"llvm.smul.with.overflow.i32"(i32 %".4", i32 %".5")
  ...
  ret i32 %".7"
}
...
  %".33" = call i32 @"hs.square"(i32 %".25")      ; in main, %".25" is n + 1
```

With `--optimize`, `hs.square` is gone; `main` stores the argument in
`square.x`, multiplies in place, and reads the answer from `square.ameen`:

```llvm
  %"square.x" = alloca i32
  %"square.ameen" = alloca i32
  ...
  store i32 %".25", i32* %"square.x"
  %".34" = load i32, i32* %"square.x"
  %".35" = load i32, i32* %"square.x"
  %".36" = call {i32, i1} @"llvm.smul.with.overflow.i32"(i32 %".34", i32 %".35")
  ...
  store i32 %".37", i32* %"square.ameen"
  %".46" = load i32, i32* %"square.ameen"
```
