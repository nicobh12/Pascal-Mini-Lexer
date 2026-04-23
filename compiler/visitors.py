"""
compiler/visitors.py
External-dispatch Visitor base class and built-in AST visitors.

Pattern
-------
Uses the External Visitor pattern — AST nodes need no accept() method.
ASTVisitor.visit(node) dispatches to visit_<ClassName> via getattr,
falling back to generic_visit when no specific handler exists.

Built-in visitors
-----------------
  ASTPrinter   — produces an indented text rendering of the AST tree
"""
from __future__ import annotations

from typing import Any, List


# ============================================================
# Base class
# ============================================================

class ASTVisitor:
    """
    Base class for all AST visitors.

    Subclass and override ``visit_<NodeTypeName>`` methods.
    Call ``self.visit(node)`` to dispatch; recurse by calling
    ``self.visit(child_node)`` explicitly inside each handler.
    """

    def visit(self, node: Any) -> Any:
        """Dispatch to ``visit_<ClassName>``, or ``generic_visit`` if absent."""
        if node is None:
            return None
        method_name = f'visit_{type(node).__name__}'
        handler = getattr(self, method_name, self.generic_visit)
        return handler(node)

    def generic_visit(self, node: Any) -> Any:
        """Default handler — subclasses may override to walk unknown nodes."""
        return None


# ============================================================
# ASTPrinter
# ============================================================

class ASTPrinter(ASTVisitor):
    """
    Pretty-prints an AST with indentation.

    Usage::

        printer = ASTPrinter()
        printer.visit(program_node)
        text = printer.result()
    """

    def __init__(self) -> None:
        self._lines: List[str] = []
        self._indent: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def result(self) -> str:
        """Return the accumulated output as a single string."""
        return '\n'.join(self._lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, text: str) -> None:
        self._lines.append('  ' * self._indent + text)

    def _child(self, label: str, node: Any) -> None:
        self._emit(label)
        if node is not None:
            self._indent += 1
            self.visit(node)
            self._indent -= 1

    def _children(self, label: str, nodes: list) -> None:
        if not nodes:
            return
        self._emit(f'{label} [{len(nodes)}]')
        self._indent += 1
        for n in nodes:
            self.visit(n)
        self._indent -= 1

    # ------------------------------------------------------------------
    # Program / Block
    # ------------------------------------------------------------------

    def visit_Program(self, node: Any) -> None:
        params = f'({", ".join(node.params)})' if node.params else ''
        self._emit(f'Program {node.name!r}{params}  line={node.line}')
        self._indent += 1
        self.visit(node.block)
        self._indent -= 1

    def visit_Block(self, node: Any) -> None:
        self._emit('Block')
        self._indent += 1
        if node.labels:
            self._emit(f'labels: {node.labels}')
        self._children('consts', node.consts)
        self._children('types', node.types)
        self._children('vars', node.vars)
        self._children('subprograms', node.subprograms)
        self._child('body:', node.body)
        self._indent -= 1

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------

    def visit_ConstDef(self, node: Any) -> None:
        self._emit(f'ConstDef {node.name!r}  line={node.line}')
        self._indent += 1
        self.visit(node.value)
        self._indent -= 1

    def visit_TypeDef(self, node: Any) -> None:
        self._emit(f'TypeDef {node.name!r}  line={node.line}')
        self._indent += 1
        self.visit(node.type_node)
        self._indent -= 1

    def visit_VarDecl(self, node: Any) -> None:
        self._emit(f'VarDecl {node.names}  line={node.line}')
        self._indent += 1
        self.visit(node.type_node)
        self._indent -= 1

    def visit_ProcDecl(self, node: Any) -> None:
        fwd = ' [forward]' if node.forward else ''
        self._emit(f'ProcDecl {node.name!r}{fwd}  line={node.line}')
        self._indent += 1
        self._children('params', node.params)
        if node.body:
            self._child('body:', node.body)
        self._indent -= 1

    def visit_FuncDecl(self, node: Any) -> None:
        fwd = ' [forward]' if node.forward else ''
        self._emit(f'FuncDecl {node.name!r} -> {node.return_type!r}{fwd}  line={node.line}')
        self._indent += 1
        self._children('params', node.params)
        if node.body:
            self._child('body:', node.body)
        self._indent -= 1

    def visit_Param(self, node: Any) -> None:
        ref = 'var ' if node.by_ref else ''
        self._emit(f'Param {ref}{node.names}: {node.type_name}  line={node.line}')

    # ------------------------------------------------------------------
    # Types
    # ------------------------------------------------------------------

    def visit_SimpleType(self, node: Any) -> None:
        self._emit(f'SimpleType {node.name!r}')

    def visit_SubrangeType(self, node: Any) -> None:
        self._emit('SubrangeType')
        self._indent += 1
        self.visit(node.low)
        self.visit(node.high)
        self._indent -= 1

    def visit_ArrayType(self, node: Any) -> None:
        packed = ' packed' if node.packed else ''
        self._emit(f'ArrayType{packed}')
        self._indent += 1
        self._children('indices', node.indices)
        self._child('element_type:', node.element_type)
        self._indent -= 1

    def visit_RecordType(self, node: Any) -> None:
        packed = ' packed' if node.packed else ''
        self._emit(f'RecordType{packed}  {len(node.fields)} fields')

    def visit_SetType(self, node: Any) -> None:
        self._emit('SetType')
        self._indent += 1
        self.visit(node.base_type)
        self._indent -= 1

    def visit_FileType(self, node: Any) -> None:
        self._emit('FileType')
        self._indent += 1
        self.visit(node.component_type)
        self._indent -= 1

    def visit_PointerType(self, node: Any) -> None:
        self._emit(f'PointerType -> {node.target!r}')

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def visit_CompoundStmt(self, node: Any) -> None:
        self._emit(f'CompoundStmt  line={node.line}')
        self._indent += 1
        for s in node.stmts:
            self.visit(s)
        self._indent -= 1

    def visit_AssignStmt(self, node: Any) -> None:
        self._emit(f'AssignStmt  line={node.line}')
        self._indent += 1
        self._child('target:', node.target)
        self._child('value:', node.value)
        self._indent -= 1

    def visit_IfStmt(self, node: Any) -> None:
        self._emit(f'IfStmt  line={node.line}')
        self._indent += 1
        self._child('cond:', node.condition)
        self._child('then:', node.then_branch)
        if node.else_branch is not None:
            self._child('else:', node.else_branch)
        self._indent -= 1

    def visit_WhileStmt(self, node: Any) -> None:
        self._emit(f'WhileStmt  line={node.line}')
        self._indent += 1
        self._child('cond:', node.condition)
        self._child('body:', node.body)
        self._indent -= 1

    def visit_ForStmt(self, node: Any) -> None:
        self._emit(f'ForStmt {node.var!r} {node.direction}  line={node.line}')
        self._indent += 1
        self._child('start:', node.start)
        self._child('end:', node.end)
        self._child('body:', node.body)
        self._indent -= 1

    def visit_RepeatStmt(self, node: Any) -> None:
        self._emit(f'RepeatStmt  line={node.line}')
        self._indent += 1
        for s in node.body:
            self.visit(s)
        self._child('until:', node.condition)
        self._indent -= 1

    def visit_CaseStmt(self, node: Any) -> None:
        self._emit(f'CaseStmt  line={node.line}')
        self._indent += 1
        self._child('expr:', node.expression)
        for labels, stmt in node.elements:
            self._emit(f'case {[str(lbl) for lbl in labels]}:')
            self._indent += 1
            self.visit(stmt)
            self._indent -= 1
        self._indent -= 1

    def visit_GotoStmt(self, node: Any) -> None:
        self._emit(f'GotoStmt {node.label}  line={node.line}')

    def visit_WritelnStmt(self, node: Any) -> None:
        self._emit(f'WritelnStmt  line={node.line}')
        self._indent += 1
        for a in node.args:
            self.visit(a)
        self._indent -= 1

    def visit_ProcCallStmt(self, node: Any) -> None:
        self._emit(f'ProcCallStmt {node.name!r}  line={node.line}')
        self._indent += 1
        for a in node.args:
            self.visit(a)
        self._indent -= 1

    def visit_WithStmt(self, node: Any) -> None:
        self._emit(f'WithStmt  line={node.line}')
        self._indent += 1
        for v in node.vars:
            self.visit(v)
        self._child('body:', node.body)
        self._indent -= 1

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def visit_IntLit(self, node: Any) -> None:
        self._emit(f'IntLit {node.value}')

    def visit_RealLit(self, node: Any) -> None:
        self._emit(f'RealLit {node.value}')

    def visit_StrLit(self, node: Any) -> None:
        self._emit(f'StrLit {node.value!r}')

    def visit_NilLit(self, node: Any) -> None:
        self._emit('NilLit')

    def visit_BoolLit(self, node: Any) -> None:
        self._emit(f'BoolLit {node.value}')

    def visit_BinOp(self, node: Any) -> None:
        self._emit(f'BinOp {node.op}  line={node.line}')
        self._indent += 1
        self.visit(node.left)
        self.visit(node.right)
        self._indent -= 1

    def visit_UnaryOp(self, node: Any) -> None:
        self._emit(f'UnaryOp {node.op}  line={node.line}')
        self._indent += 1
        self.visit(node.operand)
        self._indent -= 1

    def visit_FuncCall(self, node: Any) -> None:
        self._emit(f'FuncCall {node.name!r}  line={node.line}')
        self._indent += 1
        for a in node.args:
            self.visit(a)
        self._indent -= 1

    def visit_Var(self, node: Any) -> None:
        self._emit(f'Var {node.name!r}  line={node.line}')

    def visit_IndexVar(self, node: Any) -> None:
        self._emit(f'IndexVar  line={node.line}')
        self._indent += 1
        self._child('base:', node.base)
        self._children('indices', node.indices)
        self._indent -= 1

    def visit_FieldVar(self, node: Any) -> None:
        self._emit(f'FieldVar .{node.field_name!r}  line={node.line}')
        self._indent += 1
        self._child('base:', node.base)
        self._indent -= 1

    def visit_DerefVar(self, node: Any) -> None:
        self._emit(f'DerefVar^  line={node.line}')
        self._indent += 1
        self._child('base:', node.base)
        self._indent -= 1
