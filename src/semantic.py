"""The semantic pass: resolve every name and check every type before code generation.

It walks the tree once, after parsing, and records what the code generator
needs on the nodes: the type of each expression, the declaration each name
resolves to, the index of each field, the dua each call reaches, the folded
value of each wallahi constant, and which member duas mutate their object.

Symbol tables:
  scopes   a stack of frames, name -> DeclNode or ParamNode; every block
           pushes one. A dua body starts from a stack of its own, so it never
           sees the top-level variables.
  diwans   name -> DiwanNode: fields in order (index, type, mutability) and
           member duas (signature, mutating).
  duas     name -> DuaNode: the global duas, collected before any body is
           checked, so a body may call itself or a dua declared below it.
"""

from .ast_nodes import (
    CallNode, DeclNode, ForNode, FieldAccessNode, FieldDeclNode, IntLiteralNode, MemberCallNode,
    ParamNode, StringNode, VarNode, chain, count,
)
from .errors import CompileError

INTEGERS = ("dirham", "dinar")
BUILTINS = ("dirham", "dinar", "fatwa")
LIMITS = {"dirham": 2**31 - 1, "dinar": 2**63 - 1}
WIDTHS = {"dirham": "i32", "dinar": "i64"}


def assignable(have: str, want: str) -> bool:
    """A value fits where its type is expected; a dirham widens into a dinar."""
    return have == want or (have == "dirham" and want == "dinar")


class SemanticChecker:
    def __init__(self):
        self.scopes: list[dict] = [{}]
        self.diwans: dict = {}
        self.duas: dict = {}
        self.function = None  # the DuaNode whose body is checked, or None at the top level
        self.top_level: set[str] = set()  # names declared at the top level, for a clearer error
        self.member_calls: list = []  # (caller, call), judged once mutation is known
        self.loops = 0  # how many loops enclose the statement being checked

    def fail(self, node, message: str):
        raise CompileError(node.line, node.column, message)

    # ---------- names and types ----------

    def check_type(self, type_name: str, node):
        if type_name not in BUILTINS and type_name not in self.diwans:
            self.fail(node, f"unknown type '{type_name}' — no coin, ruling or register of that "
                            "name is known to this court")

    def check_new_name(self, node, what: str):
        """A variable, parameter or dua may not take the name of a diwan or a dua."""
        if node.name in self.diwans:
            self.fail(node, f"'{node.name}' is already the name of a diwan and cannot name {what} "
                            "— a name is given but once")
        if node.name in self.duas:
            self.fail(node, f"'{node.name}' is already the name of a dua and cannot name {what} "
                            "— a name is given but once")

    def check_assignable(self, expr, want: str, at, action: str):
        have = expr.type
        if assignable(have, want):
            return
        self.check_literal_fits(expr, want)
        if have == "dinar" and want == "dirham":
            ornament = "gold is not pressed into a silver purse"
        elif "fatwa" in (have, want) and (have in INTEGERS or want in INTEGERS):
            ornament = "a ruling is not a coin"
        else:
            ornament = "the record does not match the entry"
        self.fail(at, f"cannot {action} of type {want} with a value of type {have} — {ornament}")

    def check_literal_fits(self, expr, want: str):
        if isinstance(expr, IntLiteralNode) and want == "dirham" and expr.type == "dinar":
            self.fail(expr, f"constant {expr.value} does not fit in dirham (i32) — the purse is "
                            "too small, and the excess would be riba")

    def lookup(self, node):
        """parameters and locals, innermost first; then the fields of the caller's diwan."""
        for frame in reversed(self.scopes):
            if node.name in frame:
                return frame[node.name]
        if self.function is not None and self.function.owner:
            for field in self.diwans[self.function.owner].fields:
                if field.name == node.name:
                    return field
        if self.function is not None and node.name in self.top_level:
            self.fail(node, f"'{node.name}' is not visible inside dua '{self.function.name}' — a "
                            "supplication carries only what is handed to it")
        if node.name in self.diwans:
            self.fail(node, f"'{node.name}' is a diwan, not a value — create an object with "
                            f"{node.name}(...)")
        if node.name in self.duas:
            self.fail(node, f"'{node.name}' is a dua and is called as {node.name}(...) — a "
                            "supplication unspoken answers nothing")
        self.fail(node, f"'{node.name}' is used before its declaration — the compiler does not "
                        "acknowledge the unintroduced")

    def visible_value(self, name: str) -> bool:
        """A variable, parameter or field of this name is in scope here."""
        if any(name in frame for frame in self.scopes):
            return True
        owner = self.function.owner if self.function is not None else None
        return bool(owner) and any(f.name == name for f in self.diwans[owner].fields)

    def deep_constant_field(self, type_name: str):
        """'Diwan.field' of the first bismillah field at any depth, or None."""
        diwan = self.diwans.get(type_name)
        for field in diwan.fields if diwan else ():
            if not field.mutable:
                return f"{type_name}.{field.name}"
            if (inner := self.deep_constant_field(field.type_name)) is not None:
                return inner
        return None

    # ---------- program, diwans, duas ----------

    def visit_program(self, node):
        self.top_level = {s.name for s in node.statements if isinstance(s, DeclNode)}
        for diwan in node.diwans:
            diwan.accept(self)
        for dua in node.duas:
            if dua.name in self.duas:
                self.fail(dua, f"dua '{dua.name}' is already declared — a supplication is not "
                               "offered twice under one name")
            self.check_new_name(dua, "a dua")
            self.duas[dua.name] = dua
        members = [dua for diwan in node.diwans for dua in diwan.duas]
        for dua in members:  # a member dua may hide a global dua, but not a diwan
            if dua.name in self.diwans:
                self.fail(dua, f"'{dua.name}' is already the name of a diwan and cannot name a "
                               "member dua — a name is given but once")
        for dua in [*members, *node.duas]:
            for param in dua.params:
                self.check_type(param.type_name, param)
            self.check_type(dua.result_type, dua)
        for dua in [*members, *node.duas]:
            dua.accept(self)
        for statement in node.statements:
            statement.accept(self)
        node.exit.accept(self)
        self.settle_mutation()
        return node

    def visit_diwan(self, node):
        if node.name in self.diwans:
            self.fail(node, f"diwan '{node.name}' is already declared — a register is drawn up "
                            "but once")
        names = set()
        for field in node.fields:
            if field.name in names:
                self.fail(field, f"field '{field.name}' is already declared in diwan "
                                 f"'{node.name}' — an entry is recorded but once")
            names.add(field.name)
            if field.type_name == node.name:
                self.fail(field, f"diwan '{node.name}' cannot contain itself — a register that "
                                 "lists itself never ends")
            self.check_type(field.type_name, field)  # only the diwans above are known
        for dua in node.duas:
            if dua.name in names:
                kind = "a field" if any(f.name == dua.name for f in node.fields) else "a member dua"
                self.fail(dua, f"'{dua.name}' is already {kind} of '{node.name}' — an entry and "
                               "a duty cannot share a name")
            names.add(dua.name)
        self.diwans[node.name] = node

    def visit_dua(self, node):
        frame: dict = {}
        outer, self.scopes, self.function = self.scopes, [frame], node
        outer_loops, self.loops = self.loops, 0
        for param in node.params:
            self.check_new_name(param, "a parameter")
            if param.name in frame:
                self.fail(param, f"parameter '{param.name}' is already declared in dua "
                                 f"'{node.name}' — a name is given but once")
            frame[param.name] = param
        # The parameters and the locals of the body's own block share one frame.
        self.visit_block(node.body, new_scope=False)
        self.scopes, self.function, self.loops = outer, None, outer_loops

    # ---------- statements ----------

    def visit_block(self, node, new_scope: bool = True):
        if new_scope:
            self.scopes.append({})
        for statement in node.statements:
            statement.accept(self)
        if node.exit:
            node.exit.accept(self)
        if new_scope:
            self.scopes.pop()

    def visit_decl(self, node):
        self.check_type(node.type_name, node)
        self.check_new_name(node, "a variable")
        frame = self.scopes[-1]
        if node.name in frame:
            self.fail(node, f"'{node.name}' is already declared in this block — a name is given "
                            "but once")
        if node.kind == "wallahi" and node.type_name not in BUILTINS:
            self.fail(node, f"'{node.name}' of diwan {node.type_name} cannot be sworn with wallahi "
                            "— an object is created at runtime, and one swears only to what is "
                            "known before birth")
        node.init.accept(self)  # the name is not in scope in its own initialiser
        self.check_assignable(node.init, node.type_name, node, f"initialise '{node.name}'")
        if node.kind == "wallahi":
            node.value = self.fold(node.init, node)
        frame[node.name] = node

    def fold(self, expr, decl):
        """The value of a wallahi initialiser, computed now; it may name only constants."""
        kind = expr.visit_name
        if kind in ("int", "bool"):
            return expr.value
        if kind == "var":
            if isinstance(expr.decl, DeclNode) and expr.decl.kind == "wallahi":
                return expr.decl.value
            self.not_constant(decl, expr, f"'{expr.name}'")
        if kind == "not":
            return not self.fold(expr.operand, decl)
        if kind == "binop":
            left, right = self.fold(expr.left, decl), self.fold(expr.right, decl)
            if expr.op == "==":
                return left == right
            if expr.op == "!=":
                return left != right
            value = {"+": left + right, "-": left - right, "*": left * right}[expr.op]
            if not -LIMITS[expr.type] - 1 <= value <= LIMITS[expr.type]:
                self.fail(expr, f"'{decl.name}' overflows {expr.type} at compile time — riba "
                                "detected before the program was even born")
            return value
        described = {"read": "sual()", "field_access": f"'{chain(expr)}'"}.get(kind)
        if described is None:
            described = f"a call of '{getattr(expr, 'name', getattr(expr, 'type_name', ''))}'"
        self.not_constant(decl, expr, described)

    def not_constant(self, decl, expr, described: str):
        self.fail(expr, f"'{decl.name}' is sworn with wallahi, yet its value depends on "
                        f"{described}, known only at runtime — one does not swear to what one has "
                        "not yet seen")

    def visit_assign(self, node):
        """Every link of the target must be inshallah: the variable and each field on the way."""
        target = node.target
        target.accept(self)
        links = []
        root = target
        while isinstance(root, FieldAccessNode):
            links.append(root)
            root = root.base
        decl = root.decl
        written = node.name
        if isinstance(decl, ParamNode):
            self.fail(node, f"cannot assign to '{written}': '{root.name}' is a parameter of dua "
                            f"'{self.function.name}' — what was handed to a supplication is not "
                            "amended")
        if isinstance(decl, ForNode):
            self.fail(node, f"cannot assign to '{written}': it is the counter of 'kull' — the "
                            "loop keeps the count, and no one else")
        if isinstance(decl, FieldDeclNode):
            self.function.mutating = True
            if not decl.mutable:
                self.fail(node, f"cannot assign to '{written}': field '{self.function.owner}."
                                f"{decl.name}' is immutable (bismillah) — what was begun in the "
                                "Name is not to be amended")
        elif decl.kind == "wallahi":
            self.fail(node, f"cannot assign to '{written}': it is a constant (wallahi) — an oath "
                            "once sworn is not unsworn")
        elif decl.kind == "bismillah":
            subject = "it is" if not links else f"'{root.name}' is"
            self.fail(node, f"cannot assign to '{written}': {subject} immutable (bismillah) — what "
                            "was begun in the Name is not to be amended")
        for link in reversed(links):
            if not self.diwans[link.base.type].fields[link.index].mutable:
                self.fail(node, f"cannot assign to '{written}': '{chain(link)}' is immutable "
                                "(bismillah) — every link of the chain must be inshallah")
        if (constant := self.deep_constant_field(target.type)) is not None:
            self.fail(node, f"cannot assign to '{written}' as a whole: field '{constant}' is "
                            "immutable (bismillah) — an object is replaced only when every entry "
                            "may be amended")
        node.value.accept(self)
        self.check_assignable(node.value, target.type, node, f"assign to '{written}'")

    def visit_if(self, node):
        condition = node.condition.accept(self)
        if condition != "fatwa":
            self.fail(node, f"the condition of 'istikhara' must be fatwa, got {condition} — "
                            "guidance is not counted in coins")
        node.then_block.accept(self)
        if node.else_block:
            node.else_block.accept(self)

    def visit_while(self, node):
        condition = node.condition.accept(self)
        if condition != "fatwa":
            self.fail(node, f"the condition of 'ma_dama' must be fatwa, got {condition} — "
                            "'as long as' needs a ruling, not a coin")
        self.loops += 1
        node.body.accept(self)
        self.loops -= 1

    def visit_for(self, node):
        if node.type_name not in INTEGERS:
            self.fail(node, f"the counter '{node.name}' of 'kull' must be dirham or dinar, not "
                            f"{node.type_name} — only coins are counted")
        self.check_new_name(node, "a counter")
        for bound, verb in ((node.start, "start"), (node.end, "end")):
            bound.accept(self)  # the counter is not in scope in its own bounds
            self.check_assignable(bound, node.type_name, bound, f"{verb} the counter '{node.name}'")
        # The counter and the locals of the body share one frame, so the body
        # cannot declare a second variable of the counter's name.
        self.scopes.append({node.name: node})
        self.loops += 1
        self.visit_block(node.body, new_scope=False)
        self.loops -= 1
        self.scopes.pop()

    def visit_break(self, node):
        if not self.loops:
            self.fail(node, "'kafa' outside a loop — one cannot say \"enough\" to what was never "
                            "begun")

    def visit_exit(self, node):
        have = node.value.accept(self)
        if self.function is None:
            if have not in BUILTINS:
                self.fail(node.value, f"the program must answer with dirham, dinar or fatwa, got "
                                      f"{have} — a register cannot be the final word")
            return
        want = self.function.result_type
        if not assignable(have, want):
            self.check_literal_fits(node.value, want)
            self.fail(node.value, f"dua '{self.function.name}' must answer with {want}, got "
                                  f"{have} — a supplication is answered in the coin it asked for")

    def visit_print(self, node):
        if not isinstance(node.value, StringNode):
            node.value.accept(self)

    # ---------- expressions ----------

    def visit_binop(self, node):
        left = node.left.accept(self)
        right = node.right.accept(self)
        if node.op in ("+", "-", "*"):
            for operand in (left, right):
                if operand not in INTEGERS:
                    what = "rulings" if operand == "fatwa" else "registers"
                    self.fail(node, f"cannot apply '{node.op}' to {operand} — {what} are not "
                                    "summed")
            node.type = "dinar" if "dinar" in (left, right) else "dirham"
        elif node.op not in ("==", "!="):
            if not (left in INTEGERS and right in INTEGERS):
                self.fail(node, f"cannot order {left} and {right} with '{node.op}' — only coins "
                                "are weighed against each other")
            node.type = "fatwa"
        else:
            if not (left in INTEGERS and right in INTEGERS) and not (left == right == "fatwa"):
                ornament = ("a ruling is not a coin" if "fatwa" in (left, right)
                            else "registers are compared entry by entry, by hand")
                self.fail(node, f"cannot compare {left} with {right} — {ornament}")
            node.type = "fatwa"
        return node.type

    def visit_not(self, node):
        operand = node.operand.accept(self)
        if operand != "fatwa":
            self.fail(node, f"cannot apply 'la' to {operand} — one may refuse a ruling, not a "
                            "coin")
        node.type = "fatwa"
        return node.type

    def visit_int(self, node):
        node.type = "dirham" if node.value <= LIMITS["dirham"] else "dinar"
        return node.type

    def visit_bool(self, node):
        node.type = "fatwa"
        return node.type

    def visit_var(self, node):
        node.decl = self.lookup(node)
        node.type = node.decl.type_name
        return node.type

    def visit_field_access(self, node):
        """The field's index is found here, so the code generator never looks a name up."""
        base = node.base.accept(self)
        diwan = self.diwans.get(base)
        if diwan is None:
            self.fail(node, f"'{chain(node.base)}' is {base}, which has no field '{node.name}' — "
                            "a coin has no entries")
        for index, field in enumerate(diwan.fields):
            if field.name == node.name:
                node.index, node.type = index, field.type_name
                return node.type
        self.fail(node, f"diwan '{base}' has no field '{node.name}' — the register holds no such "
                        "entry")

    def member(self, diwan_name: str, name: str):
        return next((dua for dua in self.diwans[diwan_name].duas if dua.name == name), None)

    def visit_call(self, node):
        """Inside a member dua, f(...) looks among the duas of the same diwan first."""
        owner = self.function.owner if self.function is not None else None
        if owner and (member := self.member(owner, node.name)) is not None:
            node.function, node.on_self = member, True
            self.member_calls.append((self.function, node))
        else:
            node.function = self.duas.get(node.name)
        if node.function is None:
            where = f"pipe stage {node.stage}: " if node.stage else ""
            self.fail(node, f"{where}unknown dua '{node.name}' — no such supplication was ever "
                            "composed")
        return self.check_arguments(node)

    def visit_member_call(self, node):
        receiver = node.receiver
        if (isinstance(receiver, VarNode) and receiver.name in self.diwans
                and not self.visible_value(receiver.name)):
            self.fail(receiver, f"cannot call '{node.name}' on the diwan '{receiver.name}' itself "
                                "— duties are performed by an object, not by its register")
        type_name = receiver.accept(self)
        if type_name not in self.diwans:
            self.fail(node, f"'{chain(receiver)}' is {type_name}, which has no member duas — a "
                            "coin performs no duties")
        node.function = self.member(type_name, node.name)
        if node.function is None:
            self.fail(node, f"diwan '{type_name}' has no member dua '{node.name}' — no such duty "
                            "is recorded")
        self.member_calls.append((self.function, node))
        return self.check_arguments(node)

    def check_arguments(self, node):
        params = node.function.params
        stage = getattr(node, "stage", None)
        if len(node.args) != len(params):
            verb = "is" if len(node.args) == 1 else "are"
            where = f"pipe stage {stage}: " if stage else ""
            self.fail(node, f"{where}dua '{node.name}' takes {count(len(params), 'argument')}, "
                            f"but {len(node.args)} {verb} given — a supplication is offered with "
                            "exactly what it asks")
        for number, (arg, param) in enumerate(zip(node.args, params), start=1):
            arg.accept(self)
            if stage and number == 1:
                self.check_piped(node, arg, param)
            self.check_assignable(arg, param.type_name, arg,
                                  f"pass argument {number} of '{node.name}' as '{param.name}'")
        node.type = node.function.result_type
        return node.type

    def check_piped(self, node, arg, param):
        """The value a pipe hands to stage n must fit the first parameter of its dua."""
        if assignable(arg.type, param.type_name):
            return
        source = (f"stage {arg.stage} '{arg.name}' answers with"
                  if getattr(arg, "stage", None) else "the value piped in is")
        self.fail(node, f"pipe stage {node.stage} '{node.name}' does not fit: it takes "
                        f"{param.type_name} as '{param.name}', but {source} {arg.type} — the "
                        "pipe joins only what fits")

    def visit_new(self, node):
        fields = self.diwans[node.type_name].fields
        if len(node.args) != len(fields):
            verb = "is" if len(node.args) == 1 else "are"
            self.fail(node, f"'{node.type_name}' has {count(len(fields), 'field')}, but "
                            f"{count(len(node.args), 'value')} {verb} given — every entry of the "
                            "register receives exactly one value")
        for arg, field in zip(node.args, fields):
            arg.accept(self)
            self.check_assignable(arg, field.type_name, arg,
                                  f"initialise field '{node.type_name}.{field.name}'")
        node.type = node.type_name
        return node.type

    def visit_read(self, node):
        node.type = "dirham"
        return node.type

    # ---------- mutation ----------

    def on_own_object(self, call) -> bool:
        """The call is made on the caller's object: f() inside a member, or a field chain."""
        if isinstance(call, CallNode):
            return call.on_self
        root = call.receiver
        while isinstance(root, FieldAccessNode):
            root = root.base
        return isinstance(root.decl, FieldDeclNode)

    def settle_mutation(self):
        """A member dua is mutating if it assigns a field of its object, or calls a mutating
        member dua on its object or one of its fields. Duas may call each other in a cycle,
        so marks spread until none is added; then every mutating call is judged."""
        changed = True
        while changed:
            changed = False
            for caller, call in self.member_calls:
                if (caller is not None and caller.owner and not caller.mutating
                        and call.function.mutating and self.on_own_object(call)):
                    caller.mutating = changed = True
        for _, call in self.member_calls:
            if call.function.mutating and isinstance(call, MemberCallNode):
                self.check_mutable_receiver(call)

    def check_mutable_receiver(self, call):
        links = []
        root = call.receiver
        while isinstance(root, FieldAccessNode):
            links.append(root)
            root = root.base
        decl = root.decl
        ornament = "a duty that amends its object needs an object that may be amended"
        if isinstance(decl, ParamNode):
            self.fail(call, f"cannot call mutating dua '{call.name}' on '{root.name}': it is a "
                            f"parameter, which is never amended — {ornament}")
        if not decl.mutable:
            self.fail(call, f"cannot call mutating dua '{call.name}' on '{chain(call.receiver)}': "
                            f"'{root.name}' is immutable ({decl.kind}) — {ornament}")
        for link in reversed(links):
            if not self.diwans[link.base.type].fields[link.index].mutable:
                self.fail(call, f"cannot call mutating dua '{call.name}' on "
                                f"'{chain(call.receiver)}': '{chain(link)}' is immutable "
                                f"(bismillah) — {ornament}")
