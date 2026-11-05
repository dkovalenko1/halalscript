"""Recursive descent over the lexer's per-line token vectors.

Two cursors: the line cursor (peek_line / next_line) walks the lines, and the
token cursor (peek / eat) walks the current line, where peek() returning None
means the end of the line (NL in the grammar). A statement is one line, except
istikhara, which also consumes the lines of its blocks. One method per grammar
rule; one token of look-ahead decides every choice.

Diwans come first in a program, so when the parser meets Name( it already
knows whether Name is a diwan (a new object) or a dua (a call).
"""

from .ast_nodes import (
    AssignNode, BinOpNode, BlockNode, BoolLiteralNode, CallNode, DeclNode, DiwanNode, DuaNode,
    ExitNode, ExprNode, FieldAccessNode, FieldDeclNode, IfNode, IntLiteralNode, MemberCallNode,
    NewNode, NotNode, ParamNode, PrintNode, ProgramNode, ReadNode, StmtNode, StringNode, VarNode,
    WhileNode, chain,
)
from .errors import CompileError
from .lexer import KEYWORDS, Token

DECL_KINDS = ("wallahi", "bismillah", "inshallah")
FIELD_KINDS = ("bismillah", "inshallah")
TYPES = ("dirham", "dinar", "fatwa")
OPENERS = {"yalla": "khalas", "{": "}"}  # opener -> the closer that answers it
CLOSERS = {"khalas": "yalla", "}": "{"}
COMPARISONS = ("==", "!=", "<", "<=", ">", ">=")
OPERATORS = (":=", "+", "-", "*", "|>", *COMPARISONS)
RESERVED = frozenset(KEYWORDS.values())

EMPTY_INVOCATION = "a name invoked over nothing is an empty invocation"


class Parser:
    def __init__(self, lines: list[list[Token]]):
        self.lines = lines
        self.line_index = 0
        self.tokens: list[Token] = []
        self.index = 0
        self.diwans: set[str] = set()  # the names of the diwans declared so far

    # ---------- cursors ----------

    def peek_line(self) -> list[Token] | None:
        return self.lines[self.line_index] if self.line_index < len(self.lines) else None

    def next_line(self) -> list[Token]:
        self.tokens, self.index = self.lines[self.line_index], 0
        self.line_index += 1
        return self.tokens

    def peek(self) -> Token | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def peek_kind(self) -> str | None:
        token = self.peek()
        return token.kind if token else None

    def eat(self) -> Token:
        token = self.tokens[self.index]
        self.index += 1
        return token

    # ---------- errors ----------

    def end_position(self) -> tuple[int, int]:
        """The column right after the last token read: where the missing part belongs."""
        if not self.tokens:
            return 1, 1
        last = self.tokens[-1]
        return last.line, last.column + len(last.text)

    def error(self, message: str, at: Token | None = None) -> CompileError:
        """An error at a token, at the current token, or at the end of the line."""
        token = at or self.peek()
        if token is not None:
            return CompileError(token.line, token.column, message)
        return CompileError(*self.end_position(), message)

    def finish_line(self, after: str = "the statement"):
        token = self.peek()
        if token is None:
            return
        if token.kind == "qadarallah":
            raise self.error("'qadarallah' must begin a line of its own, right after the block "
                             "of 'istikhara' is closed")
        raise self.error(f"unexpected '{token.text}' after {after} — one deed per line; the "
                         "remainder is superfluous")

    # ---------- structure ----------

    def parse_program(self) -> ProgramNode:
        """program ::= greeting { diwan } { dua } { statement } exit_stmt"""
        greeting = self.parse_greeting()
        diwans, duas, statements = [], [], []
        while (tokens := self.peek_line()) is not None and tokens[0].kind == "diwan":
            diwans.append(self.parse_diwan())
        while (tokens := self.peek_line()) is not None and tokens[0].kind == "dua":
            duas.append(self.parse_dua(None))
        while (tokens := self.peek_line()) is not None and tokens[0].kind != "ameen":
            statements.append(self.parse_statement())
        if tokens is None:
            raise CompileError(*self.end_position(), "the program ends without 'ameen' — the "
                               "supplication is incomplete")
        self.next_line()
        exit_node = self.parse_exit()
        if (tokens := self.peek_line()) is not None:
            raise self.after_exit(tokens[0])
        return ProgramNode(greeting.line, greeting.column, statements, exit_node, diwans, duas)

    def parse_greeting(self) -> Token:  # greeting ::= "assalamu" "alaikum" NL
        if self.peek_line() is None:
            raise CompileError(1, 1, "the program must begin with 'assalamu alaikum' — even an "
                               "empty file is expected to greet")
        first = self.next_line()[0]
        if first.kind != "assalamu":
            raise self.error("the program must begin with 'assalamu alaikum' — code that enters "
                             "without greeting is turned away at the door", first)
        self.eat()
        if self.peek_kind() != "alaikum":
            raise self.error("expected 'alaikum' after 'assalamu' — a greeting abandoned halfway "
                             "is worse than none")
        self.eat()
        self.finish_line("the greeting")
        return first

    def parse_statement(self) -> StmtNode:
        """statement ::= declaration NL | assignment NL | if_stmt | while_stmt | print NL

        Consume one line, or for istikhara and ma_dama every line up to the end of their blocks.
        """
        token = self.next_line()[0]
        kind = token.kind
        if kind == "istikhara":
            return self.parse_if()
        if kind == "ma_dama":
            return self.parse_while()
        if kind in DECL_KINDS:
            statement = self.parse_declaration()
        elif kind == "bayan":
            statement = self.parse_print()
        elif kind == "ident":
            statement = self.parse_assignment()
        else:
            raise self.bad_statement_start(token)
        self.finish_line()
        return statement

    def bad_statement_start(self, token: Token) -> CompileError:
        kind = token.kind
        if kind == "qadarallah":
            message = ("'qadarallah' without a preceding 'istikhara' — one cannot accept a decree "
                       "that was never sought")
        elif kind in CLOSERS:
            message = (f"'{kind}' without a matching '{CLOSERS[kind]}' — one cannot finish what "
                       "was never started")
        elif kind in OPENERS:
            message = (f"'{kind}' may only open the block of 'istikhara', 'qadarallah', 'ma_dama', "
                       "'dua' or 'diwan', at the end of its line — a journey needs a reason to "
                       "begin")
        elif kind == "diwan":
            message = ("a 'diwan' is declared at the top of the program, before every dua and "
                       "statement — the registers are drawn up before the business begins")
        elif kind == "dua":
            message = ("a 'dua' is declared at the top level, after the diwans and before the "
                       "first statement — supplications are prepared before the work begins")
        elif kind in TYPES:
            message = (f"a declaration begins with 'wallahi', 'bismillah' or 'inshallah', not with "
                       f"'{kind}' — state the degree of certainty before the coin")
        elif kind == "assalamu":
            message = "the greeting is spoken once, on entering — not in the middle of the visit"
        else:
            message = (f"a statement cannot begin with '{token.text}' — begin with a declaration, "
                       "a name, 'istikhara' or 'ameen', as the scholars intended")
        return self.error(message, token)

    def parse_declaration(self) -> DeclNode:  # declaration ::= decl_kind type IDENT ":=" expr
        kind = self.eat().kind
        type_token = self.peek()
        following = self.tokens[self.index + 1] if self.index + 1 < len(self.tokens) else None
        if (type_token is not None and type_token.kind == "ident"
                and (following is None or following.kind == ":=")):
            raise self.error(f"'{type_token.text}' is declared without a type — even the "
                             "faithful must state what they are: dirham, dinar, fatwa or a diwan")
        type_name = self.parse_type(kind)
        name = self.expect_name(type_name)
        token = self.peek()
        if token is None:
            raise self.error(f"'{name.text}' is declared without ':=' and a value — "
                             + EMPTY_INVOCATION)
        if token.kind != ":=":
            raise self.error(f"expected ':=' after '{name.text}', got '{token.text}' — a "
                             "declaration is completed by ':=' and a value")
        self.eat()
        if self.peek() is None:
            raise self.error(f"expected a value after ':=' for '{name.text}' — " + EMPTY_INVOCATION)
        init = self.parse_expr()
        return DeclNode(name.line, name.column, name.text, kind, type_name, init)

    def parse_type(self, after: str) -> str:  # type ::= "dirham" | "dinar" | "fatwa" | IDENT
        token = self.peek()
        if token is not None and (token.kind in TYPES or token.kind == "ident"):
            return self.eat().text
        got = f"got '{token.text}'" if token else "found end of line"
        raise self.error(f"expected a type after '{after}' (dirham, dinar, fatwa or a diwan), {got}")

    def expect_name(self, after: str) -> Token:
        token = self.peek()
        if token is not None and token.kind == "ident":
            return self.eat()
        if token is not None and token.kind in RESERVED:
            raise self.error(f"'{token.text}' is a reserved word and cannot serve as a name — the "
                             "sacred vocabulary is not for private use")
        got = f"got '{token.text}'" if token else "found end of line"
        raise self.error(f"expected a name after '{after}', {got} — a coin minted without a name "
                         "belongs to no one")

    def parse_assignment(self) -> AssignNode:  # assignment ::= IDENT { "." IDENT } ":=" expr
        name = self.eat()
        target: ExprNode = VarNode(name.line, name.column, name.text)
        while self.peek_kind() == ".":
            self.eat()
            line, column, field_name = self.expect_member_name()
            target = FieldAccessNode(line, column, target, field_name)
        if self.peek_kind() == "(":
            raise self.error("a call cannot stand alone as a statement — its answer would fall "
                             "unheard; keep it with bismillah", name)
        token = self.peek()
        if token is None or token.kind != ":=":
            got = f"got '{token.text}'" if token else "found end of line"
            raise self.error(f"expected ':=' after '{chain(target)}', {got} — a name alone is a "
                             "summons without a purpose")
        self.eat()
        return AssignNode(name.line, name.column, chain(target), self.parse_expr(), target)

    def expect_member_name(self) -> tuple[int, int, str]:
        token = self.peek()
        if token is None or token.kind != "ident":
            got = f"got '{token.text}'" if token else "found end of line"
            raise self.error(f"expected a field or a member dua after '.', {got} — a register is "
                             "consulted by the name of an entry")
        self.eat()
        return token.line, token.column, token.text

    def parse_print(self) -> PrintNode:  # print ::= "bayan" "(" ( STRING | expr ) ")"
        keyword = self.eat()
        if self.peek_kind() != "(":
            raise self.error("expected '(' after 'bayan' — a proclamation is made as bayan(value)")
        opener = self.eat()
        if self.peek_kind() == ")":
            raise self.error("'bayan' requires something to proclaim — an empty proclamation "
                             "wastes the herald's breath")
        if self.peek_kind() == "string":
            token = self.eat()
            value = StringNode(token.line, token.column, token.value)
        else:
            value = self.parse_expr()
        if self.peek_kind() == ",":
            raise self.error("'bayan' proclaims one value at a time — the herald has one voice")
        self.expect_close(opener)
        return PrintNode(keyword.line, keyword.column, value)

    def expect_close(self, opener: Token):
        if self.peek_kind() != ")":
            got = f", got '{self.peek().text}'" if self.peek() else ", found end of line"
            raise self.error(f"expected ')' to close '(' at {opener.line}:{opener.column}{got} "
                             "— a parenthesis opened is a vow, and vows are kept")
        self.eat()

    # ---------- diwans and duas ----------

    def parse_diwan(self) -> DiwanNode:
        """diwan ::= "diwan" IDENT opener NL field { field } { dua } closer NL"""
        self.next_line()
        self.eat()
        name = self.expect_name("diwan")
        self.diwans.add(name.text)  # a member dua may create an object of its own diwan
        opener = self.peek()
        if opener is None or opener.kind not in OPENERS:
            got = f", got '{opener.text}'" if opener else ""
            raise self.error(f"expected 'yalla' or '{{' after the name of diwan '{name.text}'{got} "
                             "— a register is opened before it is filled")
        self.eat()
        self.finish_line(f"'{opener.text}'")
        closer = OPENERS[opener.kind]
        fields: list[FieldDeclNode] = []
        duas: list[DuaNode] = []
        while True:
            tokens = self.peek_line()
            if tokens is None:
                raise self.error(f"'{opener.text}' is never answered by '{closer}' — a journey "
                                 "begun was not concluded", opener)
            first = tokens[0]
            if first.kind in CLOSERS:
                self.close_block(opener, first)
                break
            if first.kind == "dua":
                if not fields:
                    raise self.error(f"a member dua cannot precede the first field of '{name.text}' "
                                     "— the register lists its entries before its duties", first)
                duas.append(self.parse_dua(name.text))
            elif first.kind in FIELD_KINDS:
                if duas:
                    raise self.error(f"a field of '{name.text}' follows its member duas — the "
                                     "entries of a register are written before its duties", first)
                self.next_line()
                fields.append(self.parse_field())
            elif first.kind == "wallahi":
                raise self.error("a field cannot be sworn with 'wallahi' — its value is known only "
                                 "when the object is created; use bismillah or inshallah", first)
            else:
                raise self.error(f"a diwan holds fields (bismillah or inshallah) and member duas, "
                                 f"not '{first.text}' — the register records, it does not act",
                                 first)
        if not fields:
            raise self.error(f"diwan '{name.text}' has no field — an empty register records "
                             "nothing", opener)
        delimiter = "yalla" if opener.kind == "yalla" else "brace"
        return DiwanNode(name.line, name.column, name.text, delimiter, fields, duas)

    def parse_field(self) -> FieldDeclNode:  # field ::= ( "bismillah" | "inshallah" ) type IDENT NL
        kind = self.eat().kind
        type_name = self.parse_type(kind)
        name = self.expect_name(type_name)
        if self.peek_kind() == ":=":
            raise self.error(f"field '{name.text}' takes no value in its diwan — it receives one "
                             "when the object is created")
        self.finish_line("the field")
        return FieldDeclNode(name.line, name.column, name.text, kind, type_name)

    def parse_dua(self, owner: str | None) -> DuaNode:
        """dua ::= "dua" type IDENT "(" [ param { "," param } ] ")" block   (ends with ameen)"""
        self.next_line()
        self.eat()
        result_type = self.parse_type("dua")
        name = self.expect_name(result_type)
        if self.peek_kind() != "(":
            raise self.error(f"expected '(' after the name of dua '{name.text}' — a supplication "
                             "lists what it is given, even if it is nothing")
        opener = self.eat()
        params: list[ParamNode] = []
        while self.peek_kind() != ")":
            if params:
                if self.peek_kind() != ",":
                    self.expect_close(opener)
                self.eat()
            type_name = self.parse_type("(" if not params else ",")
            param = self.expect_name(type_name)
            params.append(ParamNode(param.line, param.column, param.text, type_name))
        self.eat()
        body = self.parse_block(f"dua {name.text}")
        if body.exit is None:
            raise self.error(f"dua '{name.text}' does not end with 'ameen' — a supplication must "
                             "name its answer", name)
        return DuaNode(name.line, name.column, name.text, result_type, params, body, owner)

    def parse_if(self) -> IfNode:  # if_stmt ::= "istikhara" expr block [ "qadarallah" block ]
        keyword = self.eat()
        if self.peek() is None or self.peek_kind() in OPENERS:
            raise self.error("expected a condition after 'istikhara' — one does not seek guidance "
                             "about nothing")
        condition = self.parse_expr()
        then_block = self.parse_block("istikhara")
        else_block = None
        if (tokens := self.peek_line()) is not None and tokens[0].kind == "qadarallah":
            self.next_line()
            self.eat()
            else_block = self.parse_block("qadarallah")
        return IfNode(keyword.line, keyword.column, condition, then_block, else_block)

    def parse_while(self) -> WhileNode:  # while_stmt ::= "ma_dama" expr block
        keyword = self.eat()
        if self.peek() is None or self.peek_kind() in OPENERS:
            raise self.error("expected a condition after 'ma_dama' — 'as long as' what?")
        condition = self.parse_expr()
        return WhileNode(keyword.line, keyword.column, condition, self.parse_block("ma_dama"))

    def parse_block(self, owner: str) -> BlockNode:
        """block ::= "yalla" NL block_body "khalas" NL | "{" NL block_body "}" NL

        The opener is the last token of the owner's line; the caller's line
        cursor stands on that line.
        """
        opener = self.peek()
        if opener is None or opener.kind not in OPENERS:
            if opener is not None and opener.kind in COMPARISONS:
                raise self.chained_comparison()
            got = f", got '{opener.text}'" if opener else ""
            raise self.error(f"expected 'yalla' or '{{' after '{owner}'{got} — guidance sought must "
                             "be followed")
        self.eat()
        self.finish_line(f"'{opener.text}'")
        closer = OPENERS[opener.kind]
        statements: list[StmtNode] = []
        exit_node = None
        while True:  # block_body ::= statement { statement } [ exit_stmt ] | exit_stmt
            tokens = self.peek_line()
            if tokens is None:
                raise self.error(f"'{opener.text}' is never answered by '{closer}' — a journey "
                                 "begun was not concluded", opener)
            first = tokens[0]
            if first.kind in CLOSERS:
                self.close_block(opener, first)
                break
            if exit_node is not None:
                raise self.after_exit(first)
            if first.kind == "ameen":
                self.next_line()
                exit_node = self.parse_exit()
            else:
                statements.append(self.parse_statement())
        if not statements and exit_node is None:
            raise self.error("empty block — a block without a statement is an empty promise",
                             opener)
        delimiter = "yalla" if opener.kind == "yalla" else "brace"
        return BlockNode(opener.line, opener.column, delimiter, statements, exit_node)

    def close_block(self, opener: Token, first: Token):
        """Consume the closer line; the closer must be the partner of the opener."""
        closer = OPENERS[opener.kind]
        if first.kind != closer:
            raise self.error(f"'{opener.text}' at {opener.line}:{opener.column} must be "
                             f"closed by '{closer}', not '{first.text}' — a covenant is "
                             "closed in the tongue in which it was opened", first)
        self.next_line()
        self.eat()
        self.finish_line(f"'{first.text}'")

    def parse_exit(self) -> ExitNode:  # exit_stmt ::= "ameen" expr NL
        keyword = self.eat()
        if self.peek() is None:
            raise self.error("'ameen' requires a value — the supplication must name its answer")
        node = ExitNode(keyword.line, keyword.column, self.parse_expr())
        self.finish_line("'ameen' and its value")
        return node

    def after_exit(self, token: Token) -> CompileError:
        return self.error("statement after 'ameen' — after \"so be it\", nothing more is to be "
                          "said", token)

    # ---------- expressions ----------

    def parse_expr(self) -> ExprNode:  # expr ::= comparison { "|>" stage }
        """x |> f |> g(a) becomes g(f(x), a): each stage is a call whose first argument
        is the value of the stages before it."""
        node = self.parse_comparison()
        stage = 0
        while self.peek_kind() == "|>":
            self.eat()
            stage += 1
            token = self.peek()
            if token is None or token.kind != "ident":
                got = f"got '{token.text}'" if token else "found end of line"
                raise self.error(f"expected the name of a dua after '|>' in pipe stage {stage}, "
                                 f"{got} — a value is handed to someone, not to nothing")
            self.eat()
            if token.text in self.diwans:
                raise self.error(f"pipe stage {stage} names the diwan '{token.text}' — a value "
                                 "is piped into a dua, not into a register", token)
            args = self.parse_arguments() if self.peek_kind() == "(" else []
            node = CallNode(token.line, token.column, token.text, [node, *args], stage)
        return node

    def parse_comparison(self) -> ExprNode:  # comparison ::= arith [ compare_op arith ]
        node = self.parse_arith()
        if self.peek_kind() in COMPARISONS:
            op = self.eat()
            node = BinOpNode(op.line, op.column, op.text, node, self.parse_arith())
            if self.peek_kind() in COMPARISONS:
                raise self.chained_comparison()
        return node

    def chained_comparison(self) -> CompileError:
        return self.error(f"comparisons cannot be chained: '{self.peek().text}' follows a completed "
                          "comparison — one judgement per expression")

    def parse_arith(self) -> ExprNode:  # arith ::= term { ( "+" | "-" ) term }
        node = self.parse_term()
        while self.peek_kind() in ("+", "-"):
            op = self.eat()
            node = BinOpNode(op.line, op.column, op.text, node, self.parse_term())
        return node

    def parse_term(self) -> ExprNode:  # term ::= unary { "*" unary }
        node = self.parse_unary()
        while self.peek_kind() == "*":
            op = self.eat()
            node = BinOpNode(op.line, op.column, op.text, node, self.parse_unary())
        return node

    def parse_unary(self) -> ExprNode:  # unary ::= "la" unary | primary
        if self.peek_kind() == "la":
            keyword = self.eat()
            return NotNode(keyword.line, keyword.column, self.parse_unary())
        return self.parse_primary()

    def parse_primary(self) -> ExprNode:
        """primary ::= NUMBER | "halal" | "haram" | postfix | "(" expr ")" """
        token = self.peek()
        if token is None:
            raise self.error("expected a value, found end of line — the sentence was abandoned "
                             "mid-recitation")
        kind = token.kind
        if kind == "number":
            self.eat()
            return IntLiteralNode(token.line, token.column, token.value, token.text)
        if kind in ("halal", "haram"):
            self.eat()
            return BoolLiteralNode(token.line, token.column, kind == "halal")
        if kind in ("ident", "sual"):
            return self.parse_postfix()
        if kind == "bayan":
            raise self.error("'bayan' is a statement and has no value — a proclamation is made, "
                             "not spent")
        if kind == "string":
            raise self.error("a string literal may stand only as the argument of 'bayan' — words "
                             "are proclaimed, not computed")
        if kind == "(":
            self.eat()
            node = self.parse_expr()
            if self.peek_kind() != ")":
                got = f", got '{self.peek().text}'" if self.peek() else ", found end of line"
                raise self.error(f"expected ')' to close '(' at {token.line}:{token.column}{got} "
                                 "— a parenthesis opened is a vow, and vows are kept")
            self.eat()
            return node
        if kind == "-":
            raise self.error("'-' cannot stand before a value — there is no unary minus; write "
                             "0 - x, as the ancients did")
        if kind in OPERATORS:
            raise self.error(f"expected a value, got '{token.text}' — an operator stands where a "
                             "value was owed")
        if kind in RESERVED or kind in OPENERS or kind in CLOSERS:
            raise self.error(f"expected a value, got '{token.text}' — a keyword cannot stand in "
                             "for a value")
        raise self.error(f"expected a value, got '{token.text}'")


    def parse_postfix(self) -> ExprNode:
        """postfix ::= IDENT arguments                        (a call, or a new object)
                     | "sual" "(" ")"
                     | IDENT { "." IDENT } [ "." IDENT arguments ]
        A call ends the chain: nothing may follow its ')'."""
        token = self.eat()
        if token.kind == "sual":
            if self.peek_kind() != "(":
                raise self.error("'sual' is asked as sual() — a question must be put aloud")
            self.eat()
            if self.peek_kind() != ")":
                raise self.error("'sual' takes no arguments — the question is put to the user, "
                                 "who supplies the answer")
            self.eat()
            return self.end_of_chain(ReadNode(token.line, token.column))
        if self.peek_kind() == "(":
            args = self.parse_arguments()
            if token.text in self.diwans:
                return self.end_of_chain(NewNode(token.line, token.column, token.text, args))
            return self.end_of_chain(CallNode(token.line, token.column, token.text, args))
        node: ExprNode = VarNode(token.line, token.column, token.text)
        while self.peek_kind() == ".":
            self.eat()
            line, column, name = self.expect_member_name()
            if self.peek_kind() == "(":
                args = self.parse_arguments()
                return self.end_of_chain(MemberCallNode(line, column, node, name, args))
            node = FieldAccessNode(line, column, node, name)
        return node

    def end_of_chain(self, node: ExprNode) -> ExprNode:
        if self.peek_kind() == ".":
            raise self.error("a call ends the chain: nothing may follow its ')' — an answer is "
                             "received whole, not taken apart")
        return node

    def parse_arguments(self) -> list[ExprNode]:  # arguments ::= "(" [ expr { "," expr } ] ")"
        opener = self.eat()
        args: list[ExprNode] = []
        if self.peek_kind() != ")":
            args.append(self.parse_expr())
            while self.peek_kind() == ",":
                self.eat()
                args.append(self.parse_expr())
        self.expect_close(opener)
        return args


def parse(lines: list[list[Token]]) -> ProgramNode:
    return Parser(lines).parse_program()
