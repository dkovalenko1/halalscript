# HalalScript

> *"In the name of the Compiler, the Strict, the Unforgiving of Narrowing Conversions."*

HalalScript is a small, humorous programming language whose keywords are
everyday Arabic and Islamic expressions, each chosen so that its real meaning
matches what it does in the program. The compiler speaks like a court of
scholars handing down rulings on your code: every error states the technical
fact first, then the verdict, in a tone of **pseudo-dogmatic grandiloquent
irony**. The joke is the compiler's self-importance, never the faith.

This is **stage 1** of the course project: the language design, a hand-written
byte state-machine lexer, and a recursive-descent parser that builds an AST.
The grammar is in [`grammar.ebnf`](grammar.ebnf).

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

Two complete programs live in [`examples/`](examples): `tour.halal` walks
through every feature, with experiments in its comments that trigger the
compiler's errors, and `zakat.halal` is a small calculation. Open them in VS Code
with the [extension](#vs-code-extension) to try the highlighting, the hovers and
the live errors.

## Running the compiler

Requirements: Python 3.10 or newer. There are no dependencies to install and
nothing to build.

```sh
git clone https://github.com/dkovalenko1/halalscript.git
cd halalscript
git checkout stage1

python3 compiler.py --ast examples/tour.halal      # print the syntax tree
python3 compiler.py --tokens examples/tour.halal   # print the tokens (debugging)
python3 compiler.py examples/tour.halal            # only check the program
```

On an error the compiler prints exactly one line to stderr, prints nothing to
stdout, and exits with code 1:

```
compilation error: line 3:17: 'yalla' is never answered by 'khalas' — a journey begun was not concluded
```

## VS Code extension

[`vscode-halalscript/`](vscode-halalscript/README.md) adds HalalScript support to
VS Code for `.halal` files: highlighting, the compiler's errors underlined as you
type, keyword rulings on hover, completion, snippets, `yalla`/`khalas` bracket
matching, Eastern Arabic digit conversion, and a syntax-tree viewer.

```sh
cd vscode-halalscript && npm install && npm run package
code --install-extension halalscript-0.1.0.vsix
```

## Running the tests

```sh
python3 check.py
```

`check.py` runs every program in `tests/ok` (it must parse, and its `--ast`
output must equal the `.ast` file next to it) and every program in
`tests/err` (it must be rejected, with stderr equal to the `.expected` file next
to it), and checks that every program in `examples/` is accepted. It prints a
PASS/FAIL table, lists the failed tests, and exits non-zero
if any test fails. There are 19 valid and 38 invalid programs, each named after
what it covers.

---

## The language

### Program structure and the greeting

*"Peace be upon you."* Every program opens with
`assalamu alaikum` on its first line and ends with `ameen <value>`. One
statement per line; blank lines and `#` comments may stand anywhere.

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

`<name> := <expr>`. Only an `inshallah` variable may be assigned (checked in
stage 2).

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
| `la` | logical not (*la*, "no"); binds tightest: `la a == b` is `(la a) == b` |
| `( )` | grouping |

There is no unary minus (write `0 - x`), no `/`, no `<` or `>`.

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
In stage 1 the lexer rejects a literal larger than the largest dinar
(9223372036854775807). Stage 2 adds the checks that need types: a literal that
does not fit a dirham, narrowing dinar → dirham, and overflow while folding
`wallahi` constants. Stage 3 checks `+ - *` at runtime.

```
compilation error: line 2:22: constant 9223372036854775808 exceeds even the dinar (i64) — this is riba, an increase beyond every permitted measure
```

### Type rules and scopes (checked from stage 2)

The parser accepts any well-formed expression; the semantic pass of stage 2
will judge its types:

- a literal is a dirham if it fits, otherwise a dinar;
- `+ - *` take two integers and give the wider coin (dirham + dinar is dinar);
- `==` and `!=` take two integers (any mix) or two fatwas and give a fatwa;
- `la` and the condition of `istikhara` take a fatwa;
- a dirham widens into a dinar implicitly; nothing else converts;
- only an `inshallah` variable may be assigned; a `wallahi` initialiser may name
  only literals and other `wallahi` constants;
- a name is declared once per block and before its use; each block is a scope,
  and an inner declaration may shadow an outer one with any type.

### Names and reserved words

Names are ASCII letters, digits and `_`, not starting with a digit. Reserved:
`wallahi bismillah inshallah dirham dinar fatwa halal haram istikhara
qadarallah yalla khalas ameen la assalamu alaikum ma_dama` (`ma_dama`, "as long
as", is held for the `while` loop of a later stage). Keywords are lowercase, so
`Bismillah` is an ordinary name.

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
parentheses after the value.

Node classes (`src/ast_nodes.py`): `ASTNode` → `ProgramNode`, `BlockNode`,
`StmtNode` (`DeclNode`, `AssignNode`, `IfNode`, `ExitNode`) and `ExprNode`
(`BinOpNode`, `NotNode`, `IntLiteralNode`, `BoolLiteralNode`, `VarNode`). Every
node keeps the line and column of the token it came from.
