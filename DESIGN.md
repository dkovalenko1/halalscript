# HalalScript — Language Design (Stage 1, final)

> *"In the name of the Compiler, the Strict, the Unforgiving of Narrowing Conversions."*

This document fixes the syntax, lexical rules, grammar, AST shape and error
catalogue of HalalScript. It is the source of truth for `grammar.ebnf`, the
lexer, the parser, the tests and the README.

---

## 0. Design principles

1. **Keywords mean what they say.** Each keyword is a real Arabic / Islamic
   expression whose everyday meaning matches its role in the program.
2. **The joke is aimed at the compiler, never the faith.** The tone is
   *pseudo-dogmatic grandiloquent irony*: a compiler that sees itself as a
   court of scholars handing down rulings on your code. We mock bureaucratic
   self-importance, not belief. No Qur'anic verses in error text, no mockery
   of prayer or of the Prophet ﷺ, no names of God as identifiers.
3. **Every error stays usable.** Each message gives the **technical fact
   first**, then the ornament: `cannot assign to 'x': it is immutable
   (bismillah) — what was begun in the Name is not to be amended`. A grader who
   skips the flourish still learns what went wrong.
4. **Plain keywords, no emoji.** Every keyword is lowercase ASCII. The only
   non-ASCII input the language accepts is Eastern Arabic digits (§5.1) and
   text inside comments.
5. **Continuity with the practices.** Same pipeline (byte state-machine
   lexer → recursive descent → AST class hierarchy → `--ast` dump), same
   one-statement-per-line layout, same `compilation error: line L:C: message`
   format, same exit semantics, so stages 2 and 3 reuse the semantic pass and
   codegen design of Practices 4–5.

---

## 1. Stage-1 requirements → HalalScript feature

| Requirement (stage PDF)               | HalalScript                                              |
|---------------------------------------|----------------------------------------------------------|
| i32 equivalent                        | `dirham`                                                 |
| i64 equivalent                        | `dinar`                                                  |
| boolean type                          | `fatwa`, with literals `halal` / `haram`                 |
| constants (compile time)              | `wallahi`                                                |
| immutable variables                   | `bismillah`                                              |
| mutable variables                     | `inshallah`                                              |
| assignment                            | `x := expr`                                              |
| `==` and `!=`                         | `==` / `!=`                                              |
| type overflow checks                  | **riba** checks: lexer, semantic, runtime (§7)           |
| `if` / `else` with non-empty blocks   | `istikhara` … `qadarallah`                               |
| unique syntax elements                | Eastern Arabic numerals, two interchangeable block styles (`yalla … khalas` / `{ … }`), mandatory greeting `assalamu alaikum` (§5) |

---

## 2. Keywords, their meaning, and the official justification

Each entry gives the meaning of the expression and the *Official Ruling* — the
grandiloquent explanation that goes into the README.

### 2.1 Declarations — the three degrees of certainty

The three kinds of binding form a ladder of certainty, from the sworn to the
hoped-for.

#### `wallahi` — compile-time constant
*Arabic والله, "by God, I swear" — the oath that settles a matter beyond dispute.*

> **Official Ruling.** A *wallahi* value is sworn before the program is born.
> An oath is not taken on what one will discover later, therefore its
> initialiser may name only literals and other *wallahi* values; it is known,
> folded and judged at compile time. To reassign it would be to break an oath,
> and the compiler, which keeps careful records, will not permit the
> programmer to become a perjurer.

#### `bismillah` — immutable variable
*Arabic بسم الله, "in the name of God" — said at the beginning of an act.*

> **Official Ruling.** Declaration is the act of *naming*, and there is no
> more solemn naming than one opened with *bismillah*. The value may be
> computed at runtime — the moment of beginning is the moment of binding —
> but once begun in the Name it is not revisited. A reassignment would imply
> the Name had been invoked in error, a suggestion the compiler declines to
> entertain.

#### `inshallah` — mutable variable
*Arabic إن شاء الله, "if God wills" — said of any future that is not certain.*

> **Official Ruling.** A value declared *inshallah* is held only
> provisionally. It shall remain what it is — if God wills. He may will
> otherwise, and `:=` is how that will is expressed. The programmer who
> declares *inshallah* has confessed in advance that nothing is certain, and
> for this humility is granted the right of reassignment.

### 2.2 Types — the treasury

#### `dirham` — 32-bit signed integer (i32)
*The silver coin of the classical caliphates; the everyday small coin.*

#### `dinar` — 64-bit signed integer (i64)
*The gold coin; worth many dirhams.*

> **Official Ruling on the Coinage.** The dirham is silver and the dinar is
> gold, and as gold exceeds silver so does the dinar exceed the dirham. A
> dirham may always be placed in a purse of dinars (widening i32 → i64); a
> dinar may never be pressed into a dirham's purse, for what spills over is
> *riba* — unlawful increase — and the compiler will not be party to it.

#### `fatwa` — boolean
*A formal ruling by a qualified scholar; it answers whether a thing is permitted.*

#### `halal` / `haram` — boolean literals `true` / `false`
*Permitted / forbidden.*

> **Official Ruling.** Every *fatwa* resolves to exactly one of two verdicts:
> *halal* or *haram*. There is no third. Those who request a *makruh*
> (disliked but tolerated) boolean are referred to a language with a looser
> type system.

### 2.3 Control flow

#### `istikhara` — `if`
*Salat al-istikhara: the prayer for guidance before making a decision.*

> **Official Ruling.** Before a branch is taken, guidance is sought. The
> condition of an *istikhara* must be a *fatwa*, for guidance comes as a
> ruling and is not counted in coins. If the ruling is *halal*, the first
> block is walked.

#### `qadarallah` — `else`
*قدر الله, "God has decreed it" — said when things did not go as hoped.*

> **Official Ruling.** When the *istikhara* returns *haram*, the programmer
> does not despair; they say *qadarallah* and walk the other path. As
> acceptance follows only a hope, a *qadarallah* with no *istikhara* before
> it is rejected: one cannot accept a decree that was never sought.

#### `yalla` … `khalas`, or `{` … `}` — block open / block close
*Colloquial Arabic: "come on, let's go" … "enough, it is finished".*

> **Official Ruling.** A block is entered with eagerness (*yalla*) and left
> with finality (*khalas*). For those who arrive from the lands of C, the
> braces `{ }` are tolerated as a lawful equivalent, in the spirit of
> facilitation (*taysir*). But a block is a covenant: it must be closed in
> the tongue in which it was opened. A *yalla* answered by `}` — or a `{`
> answered by *khalas* — is a broken covenant and is rejected. A block
> holding no statement is an empty promise and is not accepted either.

#### `ameen` — program exit (`exit` of the practices)
*آمين, "so be it" — said at the end of a supplication.*

> **Official Ruling.** Every program is a supplication and every supplication
> ends with *ameen*. The value following it is the program's answer. Nothing
> may be spoken after *ameen* — not in its block, not in the program.

#### `assalamu alaikum` — mandatory program greeting
*السلام عليكم, "peace be upon you" — the greeting on entering.*

> **Official Ruling.** A program that enters without greeting is turned away
> at the door. The first line of every program is `assalamu alaikum`, in full;
> a lone `assalamu` is a greeting abandoned halfway, which is considered
> worse than none.

#### `ma_dama` — `while` (reserved, beyond stage 1)
*ما دام, literally "as long as".* Reserved now so the lexer does not change in
stage 2.

### 2.4 Operators

| Meaning         | Token   | Note                                                       |
|-----------------|---------|------------------------------------------------------------|
| assignment      | `:=`    | *tawba* — the variable turns from its former value          |
| equality        | `==`    | two witnesses                                               |
| inequality      | `!=`    |                                                             |
| logical not     | `la`    | لا, "no"                                                    |
| add / sub / mul | `+ - *` |                                                             |
| grouping        | `( )`   |                                                             |

> **Official Ruling on Equality.** Equality is established by **two
> witnesses**, `==`; a single `=` is one witness, and one witness establishes
> nothing. It is a lexical error.
>
> **Official Ruling on Negation.** The `!` is an exclamation, not an
> argument. Negation is spoken plainly: *la*. (`!` appears only inside `!=`.)
>
> **Official Ruling on Assignment.** `:=` is *tawba*: the variable turns away
> from its former value toward a new one. Only an *inshallah* variable may
> repent; the *bismillah* and the *wallahi* have nothing to repent of.

### 2.5 Reserved words

```
wallahi bismillah inshallah  dirham dinar fatwa  halal haram
istikhara qadarallah yalla khalas  ameen  la  assalamu alaikum  ma_dama
```

Keywords are lowercase; `Bismillah` or `WALLAHI` are ordinary identifiers.

---

## 3. Lexical rules

- **Encoding.** Source is UTF-8. The lexer reads **bytes**; Eastern Arabic
  digits (two bytes each, `D9 A0` … `D9 A9`) are a path in the state machine,
  the same mechanism as a keyword in letters. No regex, no `split()`.
- **Lines.** One statement per line. Newline (`\n`) ends a statement; `\r\n`
  is accepted. Blank lines and comment-only lines produce no tokens.
- **Whitespace.** Space and tab separate tokens and are otherwise ignored.
- **Comments.** `#` to end of line. Any bytes (including valid UTF-8 Arabic
  text) may appear inside a comment.
- **Identifiers.** ASCII letters, digits and `_`, not starting with a digit,
  not a reserved word.
- **Integer literals.** Unsigned decimal, written either in Western digits
  `0-9` or in **Eastern Arabic digits** `٠١٢٣٤٥٦٧٨٩` (U+0660–U+0669). One
  literal uses one script only. The token keeps its source text; the AST
  stores the normalised value.
- **Literal range (stage-1 overflow check).** A literal greater than
  9 223 372 036 854 775 807 (i64 max) is a **lexical error** — it fits no coin
  at all. Whether it fits a dirham is decided in the semantic pass (stage 2).
- **Positions.** `line:column`, both 1-based; **column counts characters
  (code points)**, so an Arabic digit is one column. Every token carries
  `kind`, `text`, `line`, `column`.
- **Two-character operators.** `:=`, `==`, `!=` use one extra state each.
  `:` alone, `=` alone, `!` alone are lexical errors.
- **Any other byte** outside a comment — including any other non-ASCII
  character — is a lexical error.

### Token kinds

```
WALLAHI BISMILLAH INSHALLAH           declaration kinds
DIRHAM DINAR FATWA                    types
HALAL HARAM                           boolean literals
ISTIKHARA QADARALLAH AMEEN            control
YALLA KHALAS LBRACE RBRACE            block delimiters
ASSALAMU ALAIKUM                      greeting
MA_DAMA                               reserved
LA                                    not
ASSIGN EQ NE PLUS MINUS STAR LPAREN RPAREN
IDENT NUMBER
```

---

## 4. Syntax

### 4.1 Program shape

```
assalamu alaikum                     # mandatory greeting, first line

wallahi dinar LIMIT := 3000000000    # compile-time constant
bismillah dirham x := ١٢             # immutable, Eastern Arabic digits
inshallah dinar total := x * 2       # mutable
bismillah fatwa ok := la (total == LIMIT)

total := total + LIMIT               # assignment (inshallah only)

istikhara ok yalla
    total := total - 1
khalas
qadarallah {
    total := 0
}

ameen total
```

### 4.2 Layout rules

- **Greeting.** The first non-blank line is exactly `assalamu alaikum`.
- **Declaration.** `<kind> <type> <name> := <expr>` on one line. Type and
  initialiser are mandatory.
- **Assignment.** `<name> := <expr>` on one line.
- **If / else.** The block opener stands at the end of the header line:
  `istikhara <expr> yalla` or `istikhara <expr> {`, and `qadarallah yalla` or
  `qadarallah {`. The closer (`khalas` or `}`) stands alone on its line.
  `qadarallah` starts the line right after the closer of the `istikhara` block.
- **Block styles.** Each block is closed with the partner of its opener.
  The then-block and the else-block may use different styles; nested blocks
  may too.
- **Blocks** hold at least one statement; blocks nest (an `istikhara` is a
  statement).
- **Exit.** `ameen <expr>` is the last statement of the program; it may also
  be the last statement of a block (as in Practice 5). Nothing follows it in
  the same block.
- **Expressions.** One comparison per expression, binding weaker than
  arithmetic: `a + 1 == b * 2`. `a == b == c` is a syntax error. `*` binds
  tighter than `+ -`, equal precedence groups left to right. `la` binds
  tightest and applies to the next factor: `la a == b` is `(la a) == b`;
  parentheses group: `la (a == b)`. No unary minus (write `0 - 5`).

### 4.3 Grammar (becomes `grammar.ebnf`)

Quoted words are the exact source spellings of tokens; `IDENT`, `NUMBER` and
`NL` are defined in the lexical part.

```ebnf
(* Blank and comment-only lines produce no tokens and no NL, as in the
   practices, so they may stand anywhere and never count as a statement. *)

(* ---------- structure ---------- *)
program     ::= greeting { statement } exit_stmt ;
greeting    ::= "assalamu" "alaikum" NL ;
statement   ::= declaration NL
              | assignment NL
              | if_stmt ;
declaration ::= decl_kind type IDENT ":=" expr ;
decl_kind   ::= "wallahi" | "bismillah" | "inshallah" ;
type        ::= "dirham" | "dinar" | "fatwa" ;
assignment  ::= IDENT ":=" expr ;
if_stmt     ::= "istikhara" expr block [ "qadarallah" block ] ;
block       ::= "yalla" NL block_body "khalas" NL
              | "{"     NL block_body "}"      NL ;
block_body  ::= statement { statement } [ exit_stmt ]
              | exit_stmt ;                            (* never empty *)
exit_stmt   ::= "ameen" expr NL ;

(* ---------- expressions ---------- *)
expr        ::= arith [ ( "==" | "!=" ) arith ] ;
arith       ::= term { ( "+" | "-" ) term } ;
term        ::= unary { "*" unary } ;
unary       ::= "la" unary | primary ;
primary     ::= NUMBER | "halal" | "haram" | IDENT | "(" expr ")" ;

(* ---------- lexical ---------- *)
IDENT        ::= letter { letter | digit } ;           (* not a reserved word *)
NUMBER       ::= digit { digit } | arabic_digit { arabic_digit } ;
                                                       (* value <= 9223372036854775807 *)
letter       ::= "a".."z" | "A".."Z" | "_" ;
digit        ::= "0".."9" ;
arabic_digit ::= "٠".."٩" ;                            (* U+0660..U+0669 *)
NL           ::= ? end of a line that holds at least one token ? ;
comment      ::= "#" { ? any byte except newline ? } ; (* discarded *)
```

### 4.4 AST class hierarchy

```
ASTNode                    line, column
├── ProgramNode            statements: [StmtNode], exit: ExitNode
├── BlockNode              delimiter: yalla|brace, statements: [StmtNode], exit: ExitNode?
├── StmtNode (abstract)
│   ├── DeclNode           name, kind: wallahi|bismillah|inshallah, type_name, init: ExprNode
│   ├── AssignNode         name, value: ExprNode
│   ├── IfNode             condition: ExprNode, then_block: BlockNode, else_block: BlockNode?
│   └── ExitNode           value: ExprNode
└── ExprNode (abstract)
    ├── BinOpNode          op (+ - * == !=), left, right
    ├── NotNode            operand
    ├── IntLiteralNode     value (int), text (source spelling)
    ├── BoolLiteralNode    value
    └── VarNode            name
```

Positions: declaration/assignment → the name; operator → the operator;
`la` → the `la`; if → `istikhara`; block → its opener; exit → `ameen`;
literal/var → itself; program → the greeting.

### 4.5 `--ast` dump format

Two-space indentation per depth; every label shows its flags and fields.

```
Program
  Decl LIMIT dinar wallahi (constant)
    Int 3000000000
  Decl x dirham bismillah (immutable)
    Int 12
  Decl total dinar inshallah (mutable)
    BinOp *
      Var x
      Int 2
  Decl ok fatwa bismillah (immutable)
    Not
      BinOp ==
        Var total
        Var LIMIT
  Assign total
    BinOp +
      Var total
      Var LIMIT
  Istikhara
    Var ok
    Block yalla
      Assign total
        BinOp -
          Var total
          Int 1
    Qadarallah
      Block brace
        Assign total
          Int 0
  Ameen
    Var total
```

`Int 12` is the value; an Arabic-digit literal additionally shows its source,
e.g. `Int 12 (١٢)`, so the dump proves the lexer read it.

---

## 5. Unique syntax elements

1. **Eastern Arabic numerals.** `bismillah dirham x := ١٢` is `12`. A literal
   mixing scripts (`١2`) is rejected. Pure lexer work over 2-byte UTF-8
   sequences — the byte state machine handles multi-byte input exactly as the
   stage PDF describes for emoji.
2. **Two block dialects** — `yalla … khalas` and `{ … }` — with the rule that a
   block is closed in the dialect it was opened in (the parser checks the
   pairing).
3. **The mandatory greeting** `assalamu alaikum`, a two-word phrase on the
   first line.

---

## 6. Typing rules (stage 2, designed now)

Same as Practice 4/5: a literal gets the narrowest coin it fits; `+ - *` on two
integers yield the wider coin; `== !=` take two integers (any mix) or two
fatwas and yield fatwa; `la` takes a fatwa; the condition of `istikhara` is a
fatwa; dirham → dinar widens implicitly, nothing else converts. Each block is a
scope; inner declarations may shadow outer names with any type. A `wallahi`
initialiser may use only literals and other `wallahi` names.

---

## 7. Overflow ("riba") checks — across all three stages

*Riba* is unlawful increase. In HalalScript it names every overflow.

| Stage | Check | Example |
|-------|-------|---------|
| 1 — lexer | literal exceeds i64 max | `inshallah dinar x := 99999999999999999999` |
| 2 — semantic | literal doesn't fit the target type | `bismillah dirham x := 3000000000` |
| 2 — semantic | narrowing dinar → dirham; int ↔ fatwa | `bismillah dirham y := someDinar` |
| 2 — semantic | `wallahi` expressions are folded at compile time; overflow while folding is a compile error | `wallahi dirham M := 2000000000 + 2000000000` |
| 3 — runtime | `+ - *` use LLVM `sadd/ssub/smul.with.overflow`; on overflow the program prints a riba message and exits non-zero | `x := x * x` repeated |

---

## 8. Error catalogue

Format fixed by the spec: one line on stderr,
`compilation error: line L:C: <message>`, non-zero exit, no output.
Messages read **technical fact — ornamental verdict**. The position is the
first character of the offending token; for "found end of line" errors it is
the column right after the last token of the line (as in Practice 3).

### 8.1 Lexical (stage 1)

| Case | Message |
|------|---------|
| unknown character | `the character '§' appears in no scripture accepted by this language` |
| invalid UTF-8 | `malformed UTF-8 byte 0xC3 — the bytes are not in a state of ritual purity` |
| lone `=` | `a single '=' is not an operator — equality requires two witnesses: '=='` |
| lone `:` | `':' must be followed by '=' — a colon alone assigns nothing and promises less` |
| lone `!` | `'!' alone is not an operator — negation is spoken plainly with 'la'` |
| letters in number | `a numeral may not be adorned with letters or '_'` |
| mixed digit scripts | `a numeral cannot serve two scripts — write it wholly in 0-9 or wholly in ٠-٩` |
| literal > i64 | `constant 99999999999999999999 exceeds even the dinar (i64) — this is riba, an increase beyond every permitted measure` |

### 8.2 Syntax (stage 1)

| Case | Message |
|------|---------|
| missing greeting | `the program must begin with 'assalamu alaikum' — code that enters without greeting is turned away at the door` |
| half greeting | `expected 'alaikum' after 'assalamu' — a greeting abandoned halfway is worse than none` |
| bad statement start | `a statement cannot begin with '+' — begin with a declaration, a name, 'istikhara' or 'ameen', as the scholars intended` |
| missing type | `'x' is declared without a type — even the faithful must state what they are: dirham, dinar or fatwa` |
| missing name | `expected a name after 'dirham' — a coin minted without a name belongs to no one` |
| missing initialiser | `'x' is declared without ':=' and a value — a name invoked over nothing is an empty invocation` |
| name without `:=` | `expected ':=' after 'x', got '5' — a name alone is a summons without a purpose` |
| expected expression | `expected a value, found end of line — the sentence was abandoned mid-recitation` |
| operator twice | `expected a value, got '*' — two operators stand where one value was owed` |
| tokens after statement | `unexpected 'y' after the statement — one deed per line; the remainder is superfluous` |
| chained comparison | `comparisons cannot be chained — one judgement per expression` |
| unbalanced `(` | `expected ')' — a parenthesis opened is a vow, and vows are kept` |
| missing block opener | `expected 'yalla' or '{' after the condition of 'istikhara' — guidance sought must be followed` |
| empty block | `empty block — a block without a statement is an empty promise` |
| unclosed block | `'yalla' is never answered by 'khalas' — a journey begun was not concluded` (or `'{' is never closed by '}'`) |
| mismatched closer | `'yalla' at 3:14 must be closed by 'khalas', not '}' — a covenant is closed in the tongue in which it was opened` |
| stray closer | `'khalas' without a matching 'yalla' — one cannot finish what was never started` |
| else without if | `'qadarallah' without a preceding 'istikhara' — one cannot accept a decree that was never sought` |
| missing `ameen` | `the program ends without 'ameen' — the supplication is incomplete` |
| statement after `ameen` | `statement after 'ameen' — after "so be it", nothing more is to be said` |

### 8.3 Semantic (stage 2 — designed now, implemented later)

| Case | Message |
|------|---------|
| undeclared | `'x' is used before its declaration — the compiler does not acknowledge the unintroduced` |
| redeclared | `'x' is already declared in this block — a name is given but once` |
| assign to bismillah | `cannot assign to 'x': it is immutable (bismillah) — what was begun in the Name is not to be amended` |
| assign to wallahi | `cannot assign to 'LIMIT': it is a constant (wallahi) — an oath once sworn is not unsworn` |
| wallahi non-constant | `'LIMIT' is sworn with wallahi, yet its value depends on 'y', known only at runtime — one does not swear to what one has not yet seen` |
| literal too big for target | `constant 3000000000 does not fit in dirham (i32) — the purse is too small, and the excess would be riba` |
| narrowing | `cannot initialise 'x' of type dirham with a value of type dinar — gold is not pressed into a silver purse` |
| bool ↔ int compare | `cannot compare fatwa with dirham — a ruling is not a coin` |
| arithmetic on bool | `cannot apply '+' to fatwa — rulings are not summed` |
| non-bool condition | `the condition of 'istikhara' must be fatwa, got dinar — guidance is not counted in coins` |
| `la` on int | `cannot apply 'la' to dirham — one may refuse a ruling, not a coin` |
| fold overflow | `'M' overflows dirham at compile time — riba detected before the program was even born` |

### 8.4 Runtime (stage 3)

Normal end: `Program exit with result <value>` (practice format; booleans
print `halal` / `haram`).
Overflow: `riba: dirham overflow in '+' at line 7:12 — the value increased
beyond its permitted measure; execution is halted in disapproval`, exit code 1.

---

## 9. Test plan (stage 1)

≥ 15 valid (`tests/ok/*.txt` + `.ast`) and ≥ 15 invalid (`tests/err/*.txt` +
`.expected`); every feature covered both ways.

| Feature | ok | err |
|---------|----|-----|
| types dirham / dinar / fatwa | `decl_all_types` | `decl_missing_type` |
| wallahi / bismillah / inshallah | `decl_all_kinds` | `decl_missing_initialiser`, `decl_missing_name` |
| assignment | `assign_expression` | `assign_missing_value`, `assign_without_operator` |
| `==` / `!=` | `compare_eq_ne` | `single_equal`, `compare_chained` |
| `la` | `not_nested` | `bang_alone` |
| precedence / parens | `arith_precedence`, `parens_grouping` | `paren_unclosed`, `operator_twice` |
| istikhara | `if_without_else`, `if_nested` | `if_missing_opener` |
| qadarallah | `if_else` | `else_without_if` |
| blocks `yalla/khalas` | `block_yalla_khalas` | `block_empty`, `block_unclosed` |
| blocks `{ }` | `block_braces` | `block_mismatched_closer`, `block_stray_closer` |
| mixed styles across blocks | `block_styles_mixed_nested` | — |
| ameen | `exit_bool`, `exit_inside_block` | `exit_missing`, `statement_after_exit` |
| greeting | (every ok test) | `greeting_missing`, `greeting_incomplete` |
| Arabic digits | `arabic_numerals` | `numeral_mixed_scripts` |
| overflow (lexer) | `literal_i64_max` | `literal_beyond_i64` |
| lexical misc | `comments_and_blank_lines` | `unknown_character`, `number_with_letters`, `tokens_after_statement` |

`check.py` runs everything and prints a PASS/FAIL table, as in the practice
repo.

---

## 10. Implementation layout

```
halalscript/
  compiler.py          # python3 compiler.py --ast input.txt
  src/errors.py        # CompileError with line:column
  src/lexer.py         # byte state machine → tokens grouped by line
  src/ast_nodes.py     # class hierarchy + dump()
  src/parser.py        # recursive descent: peek / eat / expect, one method per rule
  grammar.ebnf
  tests/ok/  tests/err/  check.py
  README.md  ai_usage.txt
```
