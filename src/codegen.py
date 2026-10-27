"""LLVM IR for a checked HalalScript tree, built only through llvmlite's IRBuilder.

The semantic pass has resolved every name, so this module never validates the
program and never looks a field up by name: a field is a gep by the index the
semantic pass stored on the node.

Layout of the module:
  - one identified struct type per diwan, %"Point" = type {i32, i32}
  - one function per global dua, named hs.<name>, and one per member dua,
    named hs.<Diwan>.<name>, whose first parameter is a pointer to the object
    ('.' cannot appear in a source name, so no dua meets main, printf or scanf)
  - main, holding the top-level statements
  - printf, scanf and exit declared from the C library, and the format strings
    as private global constants
"""

from llvmlite import ir
import llvmlite.binding as llvm

from .ast_nodes import DeclNode, FieldAccessNode, FieldDeclNode, StringNode, VarNode

I1, I8, I32, I64 = ir.IntType(1), ir.IntType(8), ir.IntType(32), ir.IntType(64)
BUILTIN_TYPES = {"fatwa": I1, "dirham": I32, "dinar": I64}
ZERO = ir.Constant(I32, 0)
FORMATS = {"dirham": b"%d", "dinar": b"%lld", "fatwa": b"%s"}
OVERFLOW_NAMES = {"+": "sadd_with_overflow", "-": "ssub_with_overflow", "*": "smul_with_overflow"}


class CodeGen:
    def __init__(self):
        self.module = ir.Module(name="halalscript", context=ir.Context())
        self.module.triple = llvm.get_default_triple()
        self.types = dict(BUILTIN_TYPES)  # source type -> LLVM type; diwans are added in order
        self.diwans = {}  # name -> DiwanNode
        self.functions = {}  # id of a DuaNode -> its ir.Function
        self.strings = {}  # bytes -> its global constant
        self.slots = {}  # id of a DeclNode or ParamNode -> its alloca
        self.function = self.entry = self.builder = None
        self.result_type = None  # the result type of the dua being built, None in main
        self.this = None  # the object pointer of the member dua being built
        self.owner = None  # the diwan of the member dua being built
        self.last_alloca = None
        char_pointer = I8.as_pointer()
        self.printf = ir.Function(self.module, ir.FunctionType(I32, [char_pointer], var_arg=True),
                                  name="printf")
        self.scanf = self.exit = None  # declared on first use

    # ---------- helpers ----------

    def begin_function(self, function: ir.Function, result_type: str | None):
        self.function, self.result_type = function, result_type
        self.entry = function.append_basic_block("entry")
        self.builder = ir.IRBuilder(self.entry)
        self.last_alloca = None
        self.this = self.owner = None

    def entry_alloca(self, type_name: str, name: str):
        """A slot at the start of the entry block, wherever the builder stands.

        A slot made inside one arm of an istikhara would not exist on the other
        path, and mem2reg promotes only the allocas of the entry block.
        """
        current = self.builder.block
        if self.last_alloca is None:
            self.builder.position_at_start(self.entry)
        else:
            self.builder.position_after(self.last_alloca)
        slot = self.last_alloca = self.builder.alloca(self.types[type_name], name=name)
        self.builder.position_at_end(current)
        return slot

    def text(self, data: bytes):
        """A pointer to a NUL-terminated global constant holding data."""
        if data not in self.strings:
            array_type = ir.ArrayType(I8, len(data) + 1)
            variable = ir.GlobalVariable(self.module, array_type, name=f"text.{len(self.strings)}")
            variable.linkage = "private"
            variable.global_constant = True
            variable.initializer = ir.Constant(array_type, bytearray(data + b"\0"))
            self.strings[data] = variable
        return self.builder.bitcast(self.strings[data], I8.as_pointer())

    def printf_call(self, fmt: bytes, *args):
        self.builder.call(self.printf, [self.text(fmt), *args])

    def emit_text(self, data: bytes):
        """Print data as it is: through %s, so a '%' in it stays a '%'.

        %s stops at a NUL byte, so each NUL of a string literal is printed
        with %c and the parts between them with %s.
        """
        for index, part in enumerate(data.split(b"\0")):
            if index:
                self.printf_call(b"%c", ZERO)
            if part:
                self.printf_call(b"%s", self.text(part))

    def coerce(self, value, have: str, want: str):
        if have == "dirham" and want == "dinar":
            return self.builder.sext(value, I64, name="wide")
        return value

    def field_pointer(self, address, index: int):
        return self.builder.gep(address, [ZERO, ir.Constant(I32, index)], inbounds=True)

    def verdict(self, value):
        """halal or haram, as a pointer to the word."""
        return self.builder.select(value, self.text(b"halal"), self.text(b"haram"))

    # ---------- program, diwans, duas ----------

    def visit_program(self, node):
        for diwan in node.diwans:
            diwan.accept(self)
        # Every function exists before any body is built, so a call may reach
        # a dua defined below it, or itself.
        duas = [dua for diwan in node.diwans for dua in diwan.duas] + node.duas
        for dua in duas:
            parameters = [self.types[param.type_name] for param in dua.params]
            if dua.owner:
                parameters.insert(0, self.types[dua.owner].as_pointer())
            signature = ir.FunctionType(self.types[dua.result_type], parameters)
            name = f"hs.{dua.owner}.{dua.name}" if dua.owner else f"hs.{dua.name}"
            function = ir.Function(self.module, signature, name=name)
            arguments = list(function.args)
            if dua.owner:
                arguments.pop(0).name = "this"
            for argument, param in zip(arguments, dua.params):
                argument.name = param.name
            self.functions[id(dua)] = function
        for dua in duas:
            dua.accept(self)
        self.begin_function(ir.Function(self.module, ir.FunctionType(I32, []), name="main"), None)
        for statement in node.statements:
            statement.accept(self)
        node.exit.accept(self)
        return self.module

    def visit_diwan(self, node):
        struct_type = self.module.context.get_identified_type(node.name)
        struct_type.set_body(*(self.types[field.type_name] for field in node.fields))
        self.types[node.name] = struct_type
        self.diwans[node.name] = node

    def visit_dua(self, node):
        function = self.functions[id(node)]
        self.begin_function(function, node.result_type)
        arguments = list(function.args)
        if node.owner:
            self.this, self.owner = arguments.pop(0), node.owner
        for argument, param in zip(arguments, node.params):
            slot = self.entry_alloca(param.type_name, param.name)
            self.builder.store(argument, slot)
            self.slots[id(param)] = slot
        node.body.accept(self)  # the body ends with ameen, so its last block has a ret

    # ---------- statements ----------

    def visit_block(self, node):
        for statement in node.statements:
            statement.accept(self)
        if node.exit:
            node.exit.accept(self)

    def visit_decl(self, node):
        if node.kind == "wallahi":
            return  # folded: every use is the constant itself
        slot = self.entry_alloca(node.type_name, node.name)
        value = node.init.accept(self)
        self.builder.store(self.coerce(value, node.init.type, node.type_name), slot)
        self.slots[id(node)] = slot

    def visit_assign(self, node):
        value = node.value.accept(self)
        value = self.coerce(value, node.value.type, node.target.type)
        self.builder.store(value, self.address(node.target))

    def visit_if(self, node):
        condition = node.condition.accept(self)
        then_bb = self.function.append_basic_block("then")
        else_bb = self.function.append_basic_block("else") if node.else_block else None
        merge_bb = self.function.append_basic_block("merge")
        self.builder.cbranch(condition, then_bb, else_bb or merge_bb)
        for block, arm in ((then_bb, node.then_block), (else_bb, node.else_block)):
            if block is None:
                continue
            self.builder.position_at_end(block)
            arm.accept(self)
            # A nested istikhara moved the builder to its own merge block; an arm
            # that ended with ameen already has its ret.
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_bb)
        self.builder.position_at_end(merge_bb)

    def visit_exit(self, node):
        value = node.value.accept(self)
        if self.result_type is not None:  # inside a dua, ameen returns the result
            self.builder.ret(self.coerce(value, node.value.type, self.result_type))
            return
        if node.value.type == "fatwa":
            self.printf_call(b"Program exit with result %s\n", self.verdict(value))
        else:
            value = self.coerce(value, node.value.type, "dinar")
            self.printf_call(b"Program exit with result %lld\n", value)
        self.builder.ret(ir.Constant(I32, 0))

    def visit_print(self, node):
        value = node.value
        if isinstance(value, StringNode):
            self.emit_text(value.value.encode("utf-8"))
        elif value.type in self.diwans:
            self.print_object(self.object_address(value), value.type)
        else:
            self.print_value(value.accept(self), value.type)
        self.emit_text(b"\n")

    def print_value(self, value, type_name: str):
        if type_name == "fatwa":
            value = self.verdict(value)
        self.printf_call(FORMATS[type_name], value)

    def print_object(self, address, type_name: str):
        """Point(x: 3, y: 4): one gep, load and printf per field, from the field table."""
        diwan = self.diwans[type_name]
        self.emit_text(type_name.encode("ascii") + b"(")
        for index, field in enumerate(diwan.fields):
            self.emit_text((", " if index else "").encode("ascii") + field.name.encode("ascii") + b": ")
            pointer = self.field_pointer(address, index)
            if field.type_name in self.diwans:
                self.print_object(pointer, field.type_name)
            else:
                self.print_value(self.builder.load(pointer), field.type_name)
        self.emit_text(b")")

    # ---------- addresses ----------

    def address(self, node):
        """The slot of a name, or a gep through the indices of a field chain."""
        if isinstance(node, FieldAccessNode):
            return self.field_pointer(self.address(node.base), node.index)
        decl = node.decl
        if isinstance(decl, FieldDeclNode):  # a field of the object, inside a member dua
            fields = self.diwans[self.owner].fields
            index = next(i for i, field in enumerate(fields) if field is decl)
            return self.field_pointer(self.this, index)
        return self.slots[id(decl)]

    def object_address(self, node):
        """The address of an object: its slot, or a temporary holding a computed value."""
        if isinstance(node, (VarNode, FieldAccessNode)):
            return self.address(node)
        slot = self.entry_alloca(node.type, "temporary")
        self.builder.store(node.accept(self), slot)
        return slot

    # ---------- expressions ----------

    def visit_binop(self, node):
        left = node.left.accept(self)
        right = node.right.accept(self)
        if node.op in OVERFLOW_NAMES:
            left = self.coerce(left, node.left.type, node.type)
            right = self.coerce(right, node.right.type, node.type)
            return self.checked_arithmetic(node, left, right)
        if node.left.type == "fatwa":
            operand_type = "fatwa"
        else:
            operand_type = "dinar" if "dinar" in (node.left.type, node.right.type) else "dirham"
        left = self.coerce(left, node.left.type, operand_type)
        right = self.coerce(right, node.right.type, operand_type)
        return self.builder.icmp_signed(node.op, left, right)

    def checked_arithmetic(self, node, left, right):
        """+ - * through llvm.s*.with.overflow; on riba the program prints why and exits 1."""
        pair = getattr(self.builder, OVERFLOW_NAMES[node.op])(left, right)
        value = self.builder.extract_value(pair, 0)
        overflow = self.builder.extract_value(pair, 1)
        self.halt_if(overflow, f"riba: {node.type} overflow in '{node.op}' at line "
                               f"{node.line}:{node.column} — the value increased beyond its "
                               "permitted measure; execution is halted in disapproval")
        return value

    def halt_if(self, condition, message: str):
        """When condition holds at runtime, print the verdict and exit with code 1."""
        with self.builder.if_then(condition, likely=False):
            self.emit_text((message + "\n").encode("utf-8"))
            if self.exit is None:
                self.exit = ir.Function(self.module, ir.FunctionType(ir.VoidType(), [I32]),
                                        name="exit")
            self.builder.call(self.exit, [ir.Constant(I32, 1)])
            self.builder.unreachable()

    def visit_not(self, node):
        return self.builder.not_(node.operand.accept(self))

    def visit_int(self, node):
        return ir.Constant(self.types[node.type], node.value)

    def visit_bool(self, node):
        return ir.Constant(I1, int(node.value))

    def visit_var(self, node):
        decl = node.decl
        if isinstance(decl, DeclNode) and decl.kind == "wallahi":
            return ir.Constant(self.types[decl.type_name], int(decl.value))
        return self.builder.load(self.address(node))

    def visit_field_access(self, node):
        return self.builder.load(self.address(node))

    def visit_new(self, node):
        """Point(3, 4) is one value of the struct type, built field by field."""
        fields = self.diwans[node.type_name].fields
        value = ir.Constant(self.types[node.type_name], ir.Undefined)
        for index, (arg, field) in enumerate(zip(node.args, fields)):
            item = self.coerce(arg.accept(self), arg.type, field.type_name)
            value = self.builder.insert_value(value, item, index)
        return value

    def call(self, node, receiver):
        args = [self.coerce(arg.accept(self), arg.type, param.type_name)
                for arg, param in zip(node.args, node.function.params)]
        return self.builder.call(self.functions[id(node.function)], receiver + args)

    def visit_call(self, node):
        return self.call(node, [self.this] if node.on_self else [])

    def visit_member_call(self, node):
        # The object is passed by address, so a mutating dua changes the original.
        return self.call(node, [self.address(node.receiver)])

    def visit_read(self, node):
        if self.scanf is None:
            self.scanf = ir.Function(self.module,
                                     ir.FunctionType(I32, [I8.as_pointer()], var_arg=True),
                                     name="scanf")
        # Read a dinar, so that a number too big for a dirham is seen rather than wrapped.
        slot = self.entry_alloca("dinar", "read")
        # scanf returns how many numbers it stored: anything but 1 means the input held
        # no number here (a word, or the end of the input), and the slot holds garbage
        stored = self.builder.call(self.scanf, [self.text(b"%lld"), slot])
        where = f"at line {node.line}:{node.column}"
        self.halt_if(self.builder.icmp_signed("!=", stored, ir.Constant(I32, 1)),
                     f"sual: expected a number {where} — the question was answered with "
                     "something that is not a coin; execution is halted")
        value = self.builder.load(slot)
        too_big = self.builder.icmp_signed(">", value, ir.Constant(I64, 2**31 - 1))
        too_small = self.builder.icmp_signed("<", value, ir.Constant(I64, -2**31))
        self.halt_if(self.builder.or_(too_big, too_small),
                     f"riba: the number read by sual {where} does not fit in dirham — the purse "
                     "is too small, and the excess would be riba; execution is halted")
        return self.builder.trunc(value, I32)


def generate(tree) -> str:
    """The module the builder printed, as text."""
    return str(tree.accept(CodeGen()))
