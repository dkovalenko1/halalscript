"""The optimizer behind --optimize: three transformations of the checked tree.

It runs after the semantic pass and before code generation. The semantic pass
has already pointed every VarNode at its declaration and every call at its
dua, so two variables of one name in different scopes are different objects:
scopes and shadowing need no further care. The optimizer keeps those links
(and the types) right as it moves nodes, so the tree needs no second check.

  unused duas       a dua that no call reachable from the program calls is
                    removed with its body; one walk from the top level finds
                    them all, including duas that only call each other
  inlining          a global dua called exactly once is replaced at its call
                    by its body (see inline_one)
  unused variables  a declaration nobody reads is removed with its
                    assignments, unless one of their values acts (see acts);
                    repeated until nothing more is removed

optimize() repeats the three until none of them changes the tree.
"""

from collections import defaultdict
from dataclasses import fields

from .ast_nodes import (
    ASTNode, AssignNode, BlockNode, CallNode, DeclNode, ExitNode, FieldAccessNode, ForNode,
    IfNode, MemberCallNode, PrintNode, ReadNode, StringNode, VarNode, BinOpNode, chain,
)

ARITHMETIC = ("+", "-", "*")


def optimize(program):
    while remove_unused_duas(program) | inline_one(program) | remove_unused_variables(program):
        pass
    return program


# ---------- walking the tree ----------

def child_nodes(node):
    """The child nodes of any node, in the order of its fields, which is the order of
    evaluation for expressions."""
    for field in fields(node):
        value = getattr(node, field.name)
        if isinstance(value, ASTNode):
            yield value
        elif isinstance(value, list):
            yield from (item for item in value if isinstance(item, ASTNode))


def walk(node):
    yield node
    for child in child_nodes(node):
        yield from walk(child)


def acts(node) -> bool:
    """A node whose evaluation the program's output can show: a call or a sual(),
    which may print or read, and + - *, which halt the program on riba."""
    return (isinstance(node, (CallNode, MemberCallNode, ReadNode))
            or isinstance(node, BinOpNode) and node.op in ARITHMETIC)


def has_effect(expr) -> bool:
    return any(acts(n) for n in walk(expr))


def root(target):
    while isinstance(target, FieldAccessNode):
        target = target.base
    return target


def bodies(program):
    """The program itself and the body of every dua, global or member."""
    yield program
    for diwan in program.diwans:
        yield from (dua.body for dua in diwan.duas)
    yield from (dua.body for dua in program.duas)


def statement_lists(program):
    """Every list of statements: the top level and every block."""
    yield program.statements
    for node in walk(program):
        if isinstance(node, BlockNode):
            yield node.statements


# ---------- unused duas ----------

def called(node):
    return (n.function for n in walk(node) if isinstance(n, (CallNode, MemberCallNode)))


def remove_unused_duas(program) -> bool:
    reached = {}
    pending = [dua for statement in (*program.statements, program.exit)
               for dua in called(statement)]
    while pending:
        dua = pending.pop()
        if id(dua) not in reached:
            reached[id(dua)] = dua
            pending.extend(called(dua.body))
    before = len(program.duas) + sum(len(diwan.duas) for diwan in program.diwans)
    program.duas = [dua for dua in program.duas if id(dua) in reached]
    for diwan in program.diwans:
        diwan.duas = [dua for dua in diwan.duas if id(dua) in reached]
    return len(program.duas) + sum(len(diwan.duas) for diwan in program.diwans) < before


# ---------- unused variables ----------

def count_uses(node, reads, writes):
    """reads: id of a declaration -> how many times it is read; writes: id -> its
    assignments. The target of an assignment is not a read."""
    if isinstance(node, AssignNode):
        writes[id(root(node.target).decl)].append(node)
        count_uses(node.value, reads, writes)
        return
    if isinstance(node, VarNode):
        reads[id(node.decl)] += 1
    for child in child_nodes(node):
        count_uses(child, reads, writes)


def remove_unused_variables(program) -> bool:
    removed_any = False
    while True:
        reads, writes = defaultdict(int), defaultdict(list)
        count_uses(program, reads, writes)
        doomed = set()
        for node in walk(program):
            # A wallahi value was computed, and checked for riba, at compile time.
            if (isinstance(node, DeclNode) and not reads[id(node)]
                    and (node.kind == "wallahi" or not has_effect(node.init))
                    and not any(has_effect(a.value) for a in writes[id(node)])):
                doomed.add(id(node))
                doomed.update(id(a) for a in writes[id(node)])
        if not doomed:
            return removed_any
        removed_any = True
        for statements in statement_lists(program):
            statements[:] = [s for s in statements if id(s) not in doomed]


# ---------- inlining ----------

def hoistable(statement) -> list:
    """The expressions of a statement that are computed once, before the statement
    acts, in the order they are computed. The condition of ma_dama is computed on
    every round, so a call in it is never inlined."""
    if isinstance(statement, DeclNode):
        return [statement.init]
    if isinstance(statement, AssignNode):
        return [statement.value]
    if isinstance(statement, PrintNode):
        return [] if isinstance(statement.value, StringNode) else [statement.value]
    if isinstance(statement, IfNode):
        return [statement.condition]
    if isinstance(statement, ExitNode):
        return [statement.value]
    if isinstance(statement, ForNode):
        return [statement.start, statement.end]
    return []


def single_exit(dua) -> bool:
    """The body leaves only through its last ameen, not from inside a block."""
    return sum(isinstance(n, ExitNode) for n in walk(dua.body)) == 1


def find_call(expressions, can_inline):
    """The first call, in the order of evaluation, that can be inlined and before
    which nothing with an effect is computed. Inlining moves the body in front of
    the statement, so it must not overtake a call, a sual() or an arithmetic
    operation that might halt on riba."""
    clean = True

    def visit(expr):
        nonlocal clean
        if isinstance(expr, CallNode) and clean and can_inline(expr):
            return expr
        for child in child_nodes(expr):
            if (found := visit(child)) is not None:
                return found
        if acts(expr):
            clean = False
        return None

    for expr in expressions:
        if (found := visit(expr)) is not None:
            return found
    return None


def replace(node, old, new):
    """Put new where old stands among the descendants of node."""
    for parent in walk(node):
        for field in fields(parent):
            value = getattr(parent, field.name)
            if value is old:
                setattr(parent, field.name, new)
                return
            if isinstance(value, list) and any(item is old for item in value):
                value[[id(item) for item in value].index(id(old))] = new
                return


def inline_one(program) -> bool:
    """Inline one call of a global dua that is called exactly once.

    f(a, b) inside a statement becomes, in front of that statement:
        bismillah <type> f.x := a          one declaration per parameter
        ...the statements of f's body...   every local renamed f.<name>
        bismillah <result> f.ameen := <the value of f's ameen>
    and the call itself becomes the variable f.ameen. A '.' cannot appear in a
    source name, so the new names never collide with the caller's; 'ameen' is a
    reserved word, so f.ameen never collides with a renamed local of f.

    Left alone: member duas (their body works on the fields of an object), a
    recursive dua (its call sits in its own body), a body that leaves through an
    ameen inside a block, and a call that is not the first effect of its statement
    or that stands in the condition of ma_dama.
    """
    counts = defaultdict(int)
    for dua in called(program):
        counts[id(dua)] += 1
    for body in bodies(program):
        for container in (body, *(n for n in walk(body) if isinstance(n, BlockNode))):
            def can_inline(call):
                dua = call.function
                return (dua.owner is None and counts[id(dua)] == 1 and dua.body is not body
                        and single_exit(dua))
            statements = container.statements
            for index, statement in enumerate([*statements, container.exit]):
                if statement is None:
                    continue
                call = find_call(hoistable(statement), can_inline)
                if call is not None:
                    statements[index:index] = expand(call, statement)
                    return True
    return False


def expand(call, statement) -> list:
    """The statements that compute the call, in front of statement, which from now on
    reads the result from a variable."""
    dua = call.function
    prefix = dua.name + "."
    params = {}
    hoisted = []
    for param, arg in zip(dua.params, call.args):
        decl = DeclNode(param.line, param.column, prefix + param.name, "bismillah",
                        param.type_name, arg)
        params[id(param)] = decl
        hoisted.append(decl)
    for node in walk(dua.body):
        if isinstance(node, (DeclNode, ForNode)):
            node.name = prefix + node.name
    for node in walk(dua.body):
        if isinstance(node, VarNode):
            node.decl = params.get(id(node.decl), node.decl)
            node.name = node.decl.name
    for node in walk(dua.body):
        if isinstance(node, AssignNode):
            node.name = chain(node.target)
    exit_value = dua.body.exit.value
    result = DeclNode(call.line, call.column, prefix + "ameen", "bismillah", dua.result_type,
                      exit_value)
    hoisted += [*dua.body.statements, result]
    value = VarNode(call.line, call.column, result.name)
    value.decl, value.type = result, call.type
    replace(statement, call, value)
    return hoisted
