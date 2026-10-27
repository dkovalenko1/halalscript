# HalalScript

> *"In the name of the Compiler, the Strict, the Unforgiving of Narrowing Conversions."*

HalalScript is a small, humorous programming language whose keywords are
everyday Arabic and Islamic expressions, each chosen so that its real meaning
matches what it does in the program. The compiler speaks like a court of
scholars handing down rulings on your code: every error states the technical
fact first, then the verdict, in a tone of **pseudo-dogmatic grandiloquent
irony**. The joke is the compiler's self-importance, never the faith.

This is **stage 2** of the course project: the language now runs. Stage 1 gave
it a hand-written byte state-machine lexer and a recursive-descent parser;
stage 2 adds functions (*dua*), structures with fields and member functions
(*diwan*), input and output (*sual* and *bayan*), a semantic pass, and LLVM IR
generated through llvmlite's builder. The grammar is in
[`grammar.ebnf`](grammar.ebnf).

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
git checkout stage2
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

## VS Code extension

[`vscode-halalscript/`](vscode-halalscript/README.md) adds HalalScript support to
VS Code for `.halal` files: highlighting, the compiler's syntax and semantic
errors underlined as you type, keyword rulings and signatures on hover,
completion (after `t.purse.`, the fields and member duas of that diwan),
snippets, `yalla`/`khalas` bracket matching, Eastern Arabic digit conversion, a
syntax-tree viewer, and a command that runs the program in a terminal.

```sh
cd vscode-halalscript && npm install && npm run package
code --install-extension halalscript-0.2.0.vsix
```

## Running the tests

```sh
python check.py                  # set LLI=/path/to/lli if lli is not on PATH
```

`check.py` compiles every program in `tests/ok` to `.ll`, runs it under `lli`,
and compares everything it prints with the `.expected` file next to it; when
`NAME.in` exists, it is the program's standard input (the input is not echoed,
so `.expected` holds only what the program prints). A program with a `.ast`
file must also print exactly that tree with `--ast`. Every program in
`tests/err` must be rejected with stderr equal to its `.expected` file, nothing
on stdout and no output file. Every program in `examples/` must compile and
run. It prints a PASS/FAIL table, lists the failed tests, and exits non-zero if
any test fails. There are 38 valid and 99 invalid programs, each named after
what it covers; all 38 valid ones run end to end.

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
| name lookup in a member dua | `member_name_shadowing`, `member_lookup_order` | `member_sees_no_top_level` |
| fields, objects, chains | `new_nested_and_copy`, `field_chain_write` | `unknown_field`, `new_wrong_value_count`, `new_field_wrong_type`, `field_declared_twice`, `diwan_contains_itself` |
| mutability of chains | `field_chain_write` | `assign_through_constant_object`, `assign_through_constant_field`, `assign_object_with_constant_field`, `assign_constant_field_in_member` |
| mutating member duas | `member_mutating_cycle`, `member_mutates_through_field`, `member_local_not_mutating`, `field_chain_write` | `mutating_call_on_constant_object`, `mutating_call_through_constant_field`, `mutating_call_on_constant_field_in_member`, `mutating_cycle_on_constant_object`, `mutating_call_on_parameter` |
| member calls | `field_chain_write`, `member_lookup_order` | `member_dua_unknown`, `member_call_on_coin`, `member_call_on_diwan` |
| printing and reading | `print_every_kind`, `read_input`, `read_not_a_number` | `bayan_as_value`, `bayan_two_values`, `bayan_empty`, `string_outside_bayan`, `sual_with_argument` |
| program and diwan order | every program with a diwan | `dua_after_statement`, `diwan_after_dua`, `dua_inside_dua`, `field_after_member_dua`, `member_dua_before_field` |
| types and declarations (stage 1 rules) | `scope_shadowing`, `decl_all_kinds` | `undeclared_name`, `redeclared_in_block`, `variable_named_like_dua`, `assign_bismillah`, `assign_wallahi`, `narrowing_dinar_to_dirham`, `compare_fatwa_with_dirham`, `arithmetic_on_fatwa`, `condition_not_fatwa`, `la_on_dirham` |
| riba | `wallahi_folding`, `runtime_riba`, `read_beyond_dirham`, `literal_i64_max` | `wallahi_fold_overflow`, `wallahi_runtime_value`, `literal_too_big_for_dirham`, `literal_beyond_i64` |

### Names and reserved words

Names are ASCII letters, digits and `_`, not starting with a digit. Reserved:
`wallahi bismillah inshallah dirham dinar fatwa halal haram istikhara
qadarallah yalla khalas ameen la assalamu alaikum ma_dama diwan dua sual
bayan` (`ma_dama`, "as long as", is held for the `while` loop of a later
stage). Keywords are lowercase, so `Bismillah` is an ordinary name.

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

`Field p.x` is a field chain; `MemberCall ... on c.center` is a chain that ends
in a member call; `Call` is a call of a global dua, or of a member dua of the
same diwan from inside it.

Node classes (`src/ast_nodes.py`): `ASTNode` → `ProgramNode`, `BlockNode`,
`DiwanNode`, `FieldDeclNode`, `DuaNode`, `ParamNode`, `StmtNode` (`DeclNode`,
`AssignNode`, `IfNode`, `ExitNode`, `PrintNode`) and `ExprNode` (`BinOpNode`,
`NotNode`, `IntLiteralNode`, `BoolLiteralNode`, `VarNode`, `FieldAccessNode`,
`CallNode`, `MemberCallNode`, `NewNode`, `ReadNode`, `StringNode`). Every node
keeps the line and column of the token it came from.

## How the compiler is built

| File | Phase |
|------|-------|
| `src/lexer.py` | byte state machine → one token vector per line |
| `src/parser.py` | recursive descent, one method per grammar rule → AST |
| `src/semantic.py` | symbol tables for variables, duas and diwans; every check above |
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
