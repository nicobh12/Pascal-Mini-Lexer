"""
compiler/ast.py
Abstract Syntax Tree node definitions for Mini-Pascal.

Every node is a frozen-ish dataclass with a 'line' field for error
reporting.  Nodes are organised by category:
  - Program / Block
  - Declarations  (ConstDef, TypeDef, VarDecl, ProcDecl, FuncDecl, Param)
  - Types         (SimpleType, SubrangeType, ArrayType, …)
  - Statements    (CompoundStmt, AssignStmt, IfStmt, …)
  - Expressions   (IntLit, RealLit, BinOp, …)
  - Errors        (ParseError, LexError)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Optional


# ============================================================
# Top-level structure
# ============================================================

@dataclass
class Program:
    name: str
    params: List[str]
    block: Any          # Block
    line: int = 0


@dataclass
class Block:
    labels: List
    consts: List        # [ConstDef]
    types: List         # [TypeDef]
    vars: List          # [VarDecl]
    subprograms: List   # [ProcDecl | FuncDecl]
    body: Any           # CompoundStmt
    line: int = 0


# ============================================================
# Declarations
# ============================================================

@dataclass
class ConstDef:
    name: str
    value: Any          # expression node
    line: int = 0


@dataclass
class TypeDef:
    name: str
    type_node: Any
    line: int = 0


@dataclass
class VarDecl:
    names: List[str]
    type_node: Any
    line: int = 0


@dataclass
class ProcDecl:
    name: str
    params: List        # [Param]
    body: Any           # Block | None  (None if forward)
    forward: bool
    line: int = 0


@dataclass
class FuncDecl:
    name: str
    params: List        # [Param]
    return_type: str
    body: Any           # Block | None
    forward: bool
    line: int = 0


@dataclass
class Param:
    names: List[str]
    type_name: str
    by_ref: bool
    line: int = 0


# ============================================================
# Types
# ============================================================

@dataclass
class SimpleType:
    name: str
    line: int = 0


@dataclass
class SubrangeType:
    low: Any
    high: Any
    line: int = 0


@dataclass
class ArrayType:
    indices: List       # [simple_type]
    element_type: Any
    packed: bool = False
    line: int = 0


@dataclass
class RecordType:
    fields: List        # [([names], type_node)]
    packed: bool = False
    line: int = 0


@dataclass
class SetType:
    base_type: Any
    packed: bool = False
    line: int = 0


@dataclass
class FileType:
    component_type: Any
    packed: bool = False
    line: int = 0


@dataclass
class PointerType:
    target: str         # name of the pointed-to type
    line: int = 0


# ============================================================
# Statements
# ============================================================

@dataclass
class CompoundStmt:
    stmts: List
    line: int = 0


@dataclass
class AssignStmt:
    target: Any
    value: Any
    line: int = 0


@dataclass
class IfStmt:
    condition: Any
    then_branch: Any
    else_branch: Optional[Any]
    line: int = 0


@dataclass
class WhileStmt:
    condition: Any
    body: Any
    line: int = 0


@dataclass
class ForStmt:
    var: str
    start: Any
    direction: str      # 'to' | 'downto'
    end: Any
    body: Any
    line: int = 0


@dataclass
class RepeatStmt:
    body: List          # list of stmts (not wrapped in CompoundStmt)
    condition: Any
    line: int = 0


@dataclass
class CaseStmt:
    expression: Any
    elements: List      # [([labels], stmt)]
    line: int = 0


@dataclass
class GotoStmt:
    label: Any          # int | str
    line: int = 0


@dataclass
class WritelnStmt:
    args: List
    line: int = 0


@dataclass
class ProcCallStmt:
    name: str
    args: List
    line: int = 0


@dataclass
class WithStmt:
    vars: List
    body: Any
    line: int = 0


# ============================================================
# Expressions
# ============================================================

@dataclass
class IntLit:
    value: int
    line: int = 0


@dataclass
class RealLit:
    value: float
    line: int = 0


@dataclass
class StrLit:
    value: str
    line: int = 0


@dataclass
class NilLit:
    line: int = 0


@dataclass
class BoolLit:
    value: bool
    line: int = 0


@dataclass
class BinOp:
    op: str             # 'PLUS' | 'MINUS' | 'TIMES' | 'AND' | 'EQUALS' | …
    left: Any
    right: Any
    line: int = 0


@dataclass
class UnaryOp:
    op: str             # 'MINUS' | 'PLUS' | 'NOT'
    operand: Any
    line: int = 0


@dataclass
class FuncCall:
    name: str
    args: List
    line: int = 0


@dataclass
class Var:
    name: str
    line: int = 0


@dataclass
class IndexVar:
    base: Any
    indices: List
    line: int = 0


@dataclass
class FieldVar:
    base: Any
    field_name: str
    line: int = 0


@dataclass
class DerefVar:
    base: Any
    line: int = 0


# ============================================================
# Error / Result types
# ============================================================

@dataclass
class ParseError:
    kind: str           # always 'syntax_error'
    line: int
    message: str

    def __str__(self) -> str:
        return f"[ParseError] {self.kind} at line {self.line}: {self.message}"


class ParseResult:
    """Container returned by parse()."""

    def __init__(self) -> None:
        self.program: Optional[Program] = None
        self.lex_errors: List = []
        self.parse_errors: List[ParseError] = []

    @property
    def ok(self) -> bool:
        return not self.parse_errors and not self.lex_errors

    def __bool__(self) -> bool:
        return self.ok
