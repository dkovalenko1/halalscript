"""The syntax tree of HalalScript.

Every node keeps the line and column of the token it came from. The tree holds
names, values, flags and child nodes, never tokens. dump() is the --ast output:
one node per line, children indented by two spaces under their parent.
"""

from dataclasses import dataclass

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
    pass


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
    visit_name = "program"

    def label(self):
        return "Program"

    def children(self):
        return (*self.statements, self.exit)


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
    type_name: str  # dirham | dinar | fatwa
    init: ExprNode
    visit_name = "decl"

    @property
    def mutable(self) -> bool:
        return self.kind == "inshallah"

    def label(self):
        return f"Decl {self.name} {self.type_name} {self.kind} ({KIND_FLAGS[self.kind]})"

    def children(self):
        return (self.init,)


@dataclass
class AssignNode(StmtNode):
    """Positioned at the assigned name."""

    name: str
    value: ExprNode
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

    def label(self):
        return f"Var {self.name}"
