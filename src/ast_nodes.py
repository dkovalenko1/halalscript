"""The syntax tree of HalalScript.

Every node keeps the line and column of the token it came from. The tree holds
names, values, flags and child nodes, never tokens. dump() is the --ast output:
one node per line, children indented by two spaces under their parent.

The semantic pass fills the fields marked "set by the semantic pass": the type
of every expression, the declaration a name resolves to, the index of a field,
the function a call reaches. The code generator reads them and looks nothing up
by name.
"""

from dataclasses import dataclass, field

KIND_FLAGS = {"wallahi": "constant", "bismillah": "immutable", "inshallah": "mutable"}


@dataclass
class ASTNode:
    line: int
    column: int

    visit_name = "node"  # accept() calls visitor.visit_<visit_name>(self)

    def label(self) -> str:
        raise NotImplementedError

    def children(self) -> tuple["ASTNode", ...]:
        return ()

    def dump(self, indent: int = 0) -> str:
        lines = [" " * indent + self.label()]
        lines.extend(child.dump(indent + 2) for child in self.children())
        return "\n".join(lines)

    def accept(self, visitor):
        return getattr(visitor, "visit_" + self.visit_name)(self)


@dataclass
class StmtNode(ASTNode):
    pass


@dataclass
class ExprNode(ASTNode):
    type = None  # dirham | dinar | fatwa | a diwan; set by the semantic pass


@dataclass
class ExitNode(StmtNode):
    """ameen <expr>: the answer of the program, or of a block that ends with it."""

    value: ExprNode
    visit_name = "exit"

    def label(self):
        return "Ameen"

    def children(self):
        return (self.value,)


@dataclass
class ProgramNode(ASTNode):
    """Positioned at the greeting."""

    statements: list[StmtNode]
    exit: ExitNode
    diwans: list["DiwanNode"] = field(default_factory=list)
    duas: list["DuaNode"] = field(default_factory=list)
    visit_name = "program"

    def label(self):
        return "Program"

    def children(self):
        return (*self.diwans, *self.duas, *self.statements, self.exit)


@dataclass
class BlockNode(ASTNode):
    """Lines between an opener and its closer; positioned at the opener."""

    delimiter: str  # "yalla" for yalla ... khalas, "brace" for { ... }
    statements: list[StmtNode]
    exit: ExitNode | None
    visit_name = "block"

    def label(self):
        return f"Block {self.delimiter}"

    def children(self):
        return (*self.statements, self.exit) if self.exit else tuple(self.statements)


@dataclass
class DeclNode(StmtNode):
    """Positioned at the declared name."""

    name: str
    kind: str  # wallahi | bismillah | inshallah
    type_name: str  # dirham | dinar | fatwa | a diwan
    init: ExprNode
    visit_name = "decl"
    value = None  # the folded value of a wallahi constant; set by the semantic pass

    @property
    def mutable(self) -> bool:
        return self.kind == "inshallah"

    def label(self):
        return f"Decl {self.name} {self.type_name} {self.kind} ({KIND_FLAGS[self.kind]})"

    def children(self):
        return (self.init,)


@dataclass
class AssignNode(StmtNode):
    """Positioned at the first name of the target."""

    name: str  # the target as written: x or c.center.x
    value: ExprNode
    target: ExprNode | None = None  # a VarNode or a FieldAccessNode
    visit_name = "assign"

    def label(self):
        return f"Assign {self.name}"

    def children(self):
        return (self.value,)


@dataclass
class IfNode(StmtNode):
    """istikhara with an optional qadarallah; positioned at 'istikhara'."""

    condition: ExprNode
    then_block: BlockNode
    else_block: BlockNode | None
    visit_name = "if"

    def label(self):
        return "Istikhara"

    def children(self):
        return (self.condition, self.then_block)

    def dump(self, indent: int = 0) -> str:
        text = super().dump(indent)
        if self.else_block is None:
            return text
        pad = " " * (indent + 2)
        return f"{text}\n{pad}Qadarallah\n{self.else_block.dump(indent + 4)}"


@dataclass
class BinOpNode(ExprNode):
    """Positioned at the operator."""

    op: str  # + - * == !=
    left: ExprNode
    right: ExprNode
    visit_name = "binop"

    def label(self):
        return f"BinOp {self.op}"

    def children(self):
        return (self.left, self.right)


@dataclass
class NotNode(ExprNode):
    """Positioned at 'la'."""

    operand: ExprNode
    visit_name = "not"

    def label(self):
        return "Not"

    def children(self):
        return (self.operand,)


@dataclass
class IntLiteralNode(ExprNode):
    value: int
    text: str  # the source spelling, Western or Eastern Arabic digits

    visit_name = "int"

    def label(self):
        if self.text == str(self.value):
            return f"Int {self.value}"
        return f"Int {self.value} ({self.text})"


@dataclass
class BoolLiteralNode(ExprNode):
    value: bool
    visit_name = "bool"

    def label(self):
        return f"Bool {'halal' if self.value else 'haram'}"


@dataclass
class VarNode(ExprNode):
    name: str
    visit_name = "var"
    decl = None  # a DeclNode, ParamNode or FieldDeclNode; set by the semantic pass

    def label(self):
        return f"Var {self.name}"


# ---------- stage 2: diwans, duas, calls, sual and bayan ----------

@dataclass
class FieldDeclNode(ASTNode):
    """One field of a diwan; positioned at its name."""

    name: str
    kind: str  # bismillah | inshallah
    type_name: str
    visit_name = "field_decl"

    @property
    def mutable(self) -> bool:
        return self.kind == "inshallah"

    def label(self):
        return f"Field {self.name} {self.type_name} {self.kind} ({KIND_FLAGS[self.kind]})"


@dataclass
class ParamNode(ASTNode):
    """A parameter: a copy of the argument that cannot be assigned; positioned at its name."""

    name: str
    type_name: str
    visit_name = "param"
    mutable = False

    def label(self):
        return f"Param {self.name} {self.type_name} (immutable)"


@dataclass
class DuaNode(ASTNode):
    """A function, global or member of a diwan; positioned at its name."""

    name: str
    result_type: str
    params: list[ParamNode]
    body: BlockNode  # ends with ameen
    owner: str | None = None  # the diwan of a member dua
    visit_name = "dua"
    mutating = False  # assigns a field of its object; set by the semantic pass

    def label(self):
        params = ", ".join(f"{p.type_name} {p.name}" for p in self.params)
        member = f" (member of {self.owner})" if self.owner else ""
        return f"Dua {self.name}({params}) -> {self.result_type}{member}"

    def children(self):
        return (*self.params, self.body)


@dataclass
class DiwanNode(ASTNode):
    """A structure: fields in order, then member duas; positioned at its name."""

    name: str
    delimiter: str  # yalla | brace
    fields: list[FieldDeclNode]
    duas: list[DuaNode]
    visit_name = "diwan"

    def label(self):
        return f"Diwan {self.name} {self.delimiter}"

    def children(self):
        return (*self.fields, *self.duas)


def count(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def chain(node: ExprNode) -> str:
    """The source spelling of a field chain: c.center.x."""
    if isinstance(node, FieldAccessNode):
        return f"{chain(node.base)}.{node.name}"
    return node.name


@dataclass
class FieldAccessNode(ExprNode):
    """base.name, where base is a name or a shorter chain; positioned at the field name."""

    base: ExprNode
    name: str
    visit_name = "field_access"
    index = None  # the field's position in its diwan; set by the semantic pass

    def label(self):
        return f"Field {chain(self)}"


@dataclass
class CallNode(ExprNode):
    """name(args): a global dua, or a member dua of the same diwan; positioned at the name."""

    name: str
    args: list[ExprNode]
    visit_name = "call"
    function = None  # the DuaNode called; set by the semantic pass
    on_self = False  # a member dua called on the object of the caller; set by the semantic pass

    def label(self):
        return f"Call {self.name} ({count(len(self.args), 'argument')})"

    def children(self):
        return tuple(self.args)


@dataclass
class MemberCallNode(ExprNode):
    """receiver.name(args): the chain ends in a member call; positioned at the name."""

    receiver: ExprNode  # a VarNode or a FieldAccessNode
    name: str
    args: list[ExprNode]
    visit_name = "member_call"
    function = None  # set by the semantic pass

    def label(self):
        return f"MemberCall {self.name} on {chain(self.receiver)} ({count(len(self.args), 'argument')})"

    def children(self):
        return tuple(self.args)


@dataclass
class NewNode(ExprNode):
    """Point(3, 4): a new object, one value per field in order; positioned at the diwan name."""

    type_name: str
    args: list[ExprNode]
    visit_name = "new"

    def label(self):
        return f"New {self.type_name} ({count(len(self.args), 'value')})"

    def children(self):
        return tuple(self.args)


@dataclass
class ReadNode(ExprNode):
    """sual(): one dirham from the standard input."""

    visit_name = "read"

    def label(self):
        return "Sual"


@dataclass
class StringNode(ExprNode):
    """A string literal; it stands only as the argument of bayan."""

    value: str
    visit_name = "string"

    def label(self):
        return f'String "{self.value}"'


@dataclass
class PrintNode(StmtNode):
    """bayan(value): prints the value and a newline; positioned at 'bayan'."""

    value: ExprNode
    visit_name = "print"

    def label(self):
        return "Bayan"

    def children(self):
        return (self.value,)
