"""
compiler/semantic.py
Layer 3 — Semantic analysis for Mini-Pascal using the Visitor pattern.

Checks
------
  - Duplicate declarations within the same scope
  - Forward-declaration resolution (forward + body is NOT a duplicate)
  - Undeclared identifier references
  - Basic type compatibility (assignment, arithmetic)
  - Arity validation for user-defined function/procedure calls
  - WITH statement opens the record's field scope

Public API
----------
  analyze(program: Program) -> SemanticResult
  SemanticResult                       — .ok, .errors
  SemanticError                        — .kind, .line, .message
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from compiler.ast import (
    Program, Block,
    ConstDef, TypeDef, VarDecl, ProcDecl, FuncDecl, Param,
    SimpleType, SubrangeType, ArrayType, RecordType, SetType, FileType,
    PointerType,
    CompoundStmt, AssignStmt, IfStmt, WhileStmt, ForStmt, RepeatStmt,
    CaseStmt, GotoStmt, WritelnStmt, ProcCallStmt, WithStmt,
    IntLit, RealLit, StrLit, NilLit, BoolLit, BinOp, UnaryOp, FuncCall,
    Var, IndexVar, FieldVar, DerefVar,
)
from compiler.visitors import ASTVisitor


# ============================================================
# Public result types
# ============================================================

@dataclass
class SemanticError:
    kind: str       # e.g. 'undeclared_identifier', 'type_mismatch', …
    line: int
    message: str

    def __str__(self) -> str:
        return f"[SemanticError] {self.kind} at line {self.line}: {self.message}"


class SemanticResult:
    def __init__(self) -> None:
        self.errors: List[SemanticError] = []
        # List of (scope_name, symbol_name, type_repr) recorded during analysis.
        # Populated only when the analyzer is run; empty until then.
        self.symbol_log: List[Tuple[str, str, str]] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def __bool__(self) -> bool:
        return self.ok


# ============================================================
# Internal type descriptors
# ============================================================

class _Type:
    """Internal type descriptor used during analysis."""


class _IntType(_Type):
    def __repr__(self) -> str: return 'integer'


class _RealType(_Type):
    def __repr__(self) -> str: return 'real'


class _BoolType(_Type):
    def __repr__(self) -> str: return 'boolean'


class _CharType(_Type):
    def __repr__(self) -> str: return 'char'


class _StringType(_Type):
    def __repr__(self) -> str: return 'string'


class _NilType(_Type):
    def __repr__(self) -> str: return 'nil'


class _AnyType(_Type):
    """Sentinel — used for unknown types during error recovery."""
    def __repr__(self) -> str: return '<any>'


class _ArrayType(_Type):
    def __init__(self, element_type: _Type) -> None:
        self.element_type = element_type

    def __repr__(self) -> str: return f'array of {self.element_type}'


class _RecordType(_Type):
    def __init__(self, fields: Dict[str, _Type]) -> None:
        self.fields = fields

    def __repr__(self) -> str: return 'record'


class _PointerType(_Type):
    def __init__(self, target_name: str) -> None:
        self.target_name = target_name

    def __repr__(self) -> str: return f'^{self.target_name}'


class _SetType(_Type):
    def __init__(self, base_type: _Type) -> None:
        self.base_type = base_type

    def __repr__(self) -> str: return f'set of {self.base_type}'


class _FileType(_Type):
    def __init__(self, component_type: _Type) -> None:
        self.component_type = component_type

    def __repr__(self) -> str: return f'file of {self.component_type}'


class _ProcType(_Type):
    """
    Type of a procedure.

    Parameters
    ----------
    params      list of (names, type, by_ref) triples from the declaration
    check_arity True for user-defined procedures; False for built-ins whose
                arity we do not validate (e.g. write, read, halt).
    """
    def __init__(self, params: list, check_arity: bool = True) -> None:
        self.params = params
        self.check_arity = check_arity

    def __repr__(self) -> str: return 'procedure'


class _FuncType(_Type):
    """
    Type of a function.

    Parameters
    ----------
    params      list of (names, type, by_ref) triples
    return_type inferred return type
    check_arity True for user-defined functions; False for built-ins.
    """
    def __init__(self, params: list, return_type: _Type,
                 check_arity: bool = True) -> None:
        self.params = params
        self.return_type = return_type
        self.check_arity = check_arity

    def __repr__(self) -> str: return f'function: {self.return_type}'


# Type singletons
T_INT  = _IntType()
T_REAL = _RealType()
T_BOOL = _BoolType()
T_CHAR = _CharType()
T_STR  = _StringType()
T_NIL  = _NilType()
T_ANY  = _AnyType()

# Built-in Pascal identifiers pre-loaded into the global scope.
# PROBLEMA 11: 'writeln' removed — the parser emits WritelnStmt, never a ProcCallStmt.
# PROBLEMA 12: 'true'/'false' removed — the parser now emits BoolLit directly.
# All built-ins use check_arity=False so variadic/overloaded builtins pass silently.
_BUILTINS: Dict[str, _Type] = {
    'integer': T_INT,
    'real':    T_REAL,
    'boolean': T_BOOL,
    'char':    T_CHAR,
    'string':  T_STR,
    'text':    _FileType(T_CHAR),
    # Standard functions — arity not checked (they accept flexible argument lists)
    'abs':     _FuncType([], T_ANY,  check_arity=False),
    'sqr':     _FuncType([], T_INT,  check_arity=False),
    'sqrt':    _FuncType([], T_REAL, check_arity=False),
    'round':   _FuncType([], T_INT,  check_arity=False),
    'trunc':   _FuncType([], T_INT,  check_arity=False),
    'ord':     _FuncType([], T_INT,  check_arity=False),
    'chr':     _FuncType([], T_CHAR, check_arity=False),
    'pred':    _FuncType([], T_ANY,  check_arity=False),
    'succ':    _FuncType([], T_ANY,  check_arity=False),
    'odd':     _FuncType([], T_BOOL, check_arity=False),
    'eof':     _FuncType([], T_BOOL, check_arity=False),
    'eoln':    _FuncType([], T_BOOL, check_arity=False),
    'sin':     _FuncType([], T_REAL, check_arity=False),
    'cos':     _FuncType([], T_REAL, check_arity=False),
    'exp':     _FuncType([], T_REAL, check_arity=False),
    'ln':      _FuncType([], T_REAL, check_arity=False),
    'max':     _FuncType([], T_ANY,  check_arity=False),
    'min':     _FuncType([], T_ANY,  check_arity=False),
    'length':  _FuncType([], T_INT,  check_arity=False),
    # Standard procedures — arity not checked
    'write':   _ProcType([], check_arity=False),
    'read':    _ProcType([], check_arity=False),
    'readln':  _ProcType([], check_arity=False),
    'new':     _ProcType([], check_arity=False),
    'dispose': _ProcType([], check_arity=False),
    'halt':    _ProcType([], check_arity=False),
}


# ============================================================
# Symbol table — lexically-scoped chain of dictionaries
# ============================================================

class _Scope:
    def __init__(self, parent: Optional['_Scope'] = None,
                 name: str = '<global>') -> None:
        self.parent = parent
        self.name = name
        self._symbols: Dict[str, Any] = {}

    def define(self, ident: str, entry: Any) -> bool:
        """Define *ident* in this scope. Returns False if already defined."""
        key = ident.lower()
        if key in self._symbols:
            return False
        self._symbols[key] = entry
        return True

    def update(self, ident: str, entry: Any) -> None:
        """Force-update an existing entry (used for forward → body resolution)."""
        self._symbols[ident.lower()] = entry

    def lookup(self, ident: str) -> Optional[Any]:
        """Look up *ident* in this scope and all enclosing scopes."""
        key = ident.lower()
        if key in self._symbols:
            return self._symbols[key]
        return self.parent.lookup(ident) if self.parent else None

    def lookup_local(self, ident: str) -> Optional[Any]:
        """Look up *ident* in this scope only."""
        return self._symbols.get(ident.lower())


# ============================================================
# Semantic Analyzer — Visitor implementation
# ============================================================

class SemanticAnalyzer(ASTVisitor):
    """
    Walks the AST and enforces Mini-Pascal semantic rules.

    Implements the Visitor pattern: each AST node type has a dedicated
    ``visit_<NodeType>`` method.  The base ``ASTVisitor.visit()`` dispatches
    via ``getattr`` — no ``accept()`` required on the nodes themselves.
    """

    def __init__(self) -> None:
        self._errors: List[SemanticError] = []
        self._scope: _Scope = _Scope(name='<global>')
        # BUG 2: forward declarations — keyed by (scope object id, name)
        # so that same-named identifiers in different scopes are tracked
        # independently.
        self._forward_decls: Set[Tuple[int, str]] = set()
        # Records every user-defined symbol as (scope_name, ident, type_repr).
        self._symbol_log: List[Tuple[str, str, str]] = []
        # Pre-load built-in Pascal identifiers
        for name, t in _BUILTINS.items():
            self._scope.define(name, t)

    # ----------------------------------------------------------
    # Error helpers
    # ----------------------------------------------------------

    def _err(self, kind: str, line: int, msg: str) -> None:
        self._errors.append(SemanticError(kind=kind, line=line, message=msg))

    def _undeclared(self, name: str, line: int) -> None:
        self._err('undeclared_identifier', line,
                  f"identifier '{name}' is not declared")

    def _duplicate(self, name: str, line: int) -> None:
        self._err('duplicate_declaration', line,
                  f"'{name}' is already declared in this scope")

    # ----------------------------------------------------------
    # Scope helpers
    # ----------------------------------------------------------

    def _push_scope(self, name: str = '<block>') -> None:
        self._scope = _Scope(parent=self._scope, name=name)

    def _pop_scope(self) -> None:
        assert self._scope.parent is not None
        self._scope = self._scope.parent

    def _define(self, name: str, entry: Any, line: int) -> None:
        if not self._scope.define(name, entry):
            self._duplicate(name, line)
        else:
            self._symbol_log.append((self._scope.name, name, repr(entry)))

    # ----------------------------------------------------------
    # Type resolution helpers
    # ----------------------------------------------------------

    def _resolve_type(self, type_node: Any) -> _Type:
        """Resolve an AST type node to an internal _Type descriptor."""
        if type_node is None:
            return T_ANY
        if isinstance(type_node, SimpleType):
            entry = self._scope.lookup(type_node.name)
            if entry is None:
                self._undeclared(type_node.name, type_node.line)
                return T_ANY
            return entry if isinstance(entry, _Type) else T_ANY
        if isinstance(type_node, SubrangeType):
            # BUG 8: char subranges ('A'..'Z') resolve to T_CHAR, not T_INT.
            low = type_node.low
            if isinstance(low, StrLit) and len(low.value) == 1:
                return T_CHAR
            return T_INT
        if isinstance(type_node, ArrayType):
            return _ArrayType(self._resolve_type(type_node.element_type))
        if isinstance(type_node, RecordType):
            fields: Dict[str, _Type] = {}
            for names, t in type_node.fields:
                ft = self._resolve_type(t)
                for n in names:
                    fields[n.lower()] = ft
            return _RecordType(fields)
        if isinstance(type_node, SetType):
            return _SetType(self._resolve_type(type_node.base_type))
        if isinstance(type_node, FileType):
            return _FileType(self._resolve_type(type_node.component_type))
        if isinstance(type_node, PointerType):
            return _PointerType(type_node.target)
        return T_ANY

    def _compatible(self, lhs: _Type, rhs: _Type) -> bool:
        """Return True when *rhs* can be assigned to a slot of type *lhs*."""
        if type(lhs) is type(rhs):
            return True
        if isinstance(lhs, _AnyType) or isinstance(rhs, _AnyType):
            return True
        # Integer widens to real
        if isinstance(lhs, _RealType) and isinstance(rhs, _IntType):
            return True
        # nil is assignable to any pointer
        if isinstance(lhs, _PointerType) and isinstance(rhs, _NilType):
            return True
        # BUG 4: a single-character string literal is compatible with char.
        # Pascal standard allows 'A' to be assigned to a char variable; the
        # semantic layer cannot distinguish length-1 strings from longer ones
        # without tracking literal values through the type system, so we allow
        # any string-to-char assignment (length violation is a runtime concern).
        if isinstance(lhs, _CharType) and isinstance(rhs, _StringType):
            return True
        return False

    def _expected_arity(self, entry: Any) -> Optional[int]:
        """
        Return the expected argument count for a user-defined callable, or
        None when arity checking is disabled (built-ins).
        """
        if isinstance(entry, (_FuncType, _ProcType)) and entry.check_arity:
            return sum(len(names) for names, *_ in entry.params)
        return None

    # ----------------------------------------------------------
    # Visitor — Program / Block
    # ----------------------------------------------------------

    def visit_Program(self, node: Program) -> SemanticResult:
        self._push_scope(node.name)
        self.visit(node.block)
        self._pop_scope()
        result = SemanticResult()
        result.errors = list(self._errors)
        result.symbol_log = list(self._symbol_log)
        return result

    def visit_Block(self, node: Block) -> None:
        # Pascal block ordering: labels → consts → types → vars → subprograms → body
        for lbl in node.labels:
            self._define(str(lbl), T_INT, 0)
        for c in node.consts:
            self.visit(c)
        for td in node.types:
            self.visit(td)
        for vd in node.vars:
            self.visit(vd)
        for sub in node.subprograms:
            self.visit(sub)
        self.visit(node.body)

    # ----------------------------------------------------------
    # Visitor — Declarations
    # ----------------------------------------------------------

    def visit_ConstDef(self, node: ConstDef) -> None:
        t = self._expr_type(node.value)
        self._define(node.name, t, node.line)

    def visit_TypeDef(self, node: TypeDef) -> None:
        t = self._resolve_type(node.type_node)
        self._define(node.name, t, node.line)

    def visit_VarDecl(self, node: VarDecl) -> None:
        t = self._resolve_type(node.type_node)
        for name in node.names:
            self._define(name, t, node.line)

    def visit_ProcDecl(self, node: ProcDecl) -> None:
        fwd_key = (id(self._scope), node.name.lower())
        param_list = self._build_param_list(node.params)
        proc_type = _ProcType(param_list, check_arity=True)

        if node.forward:
            # First declaration: mark as forward-pending
            self._define(node.name, proc_type, node.line)
            self._forward_decls.add(fwd_key)
        else:
            if fwd_key in self._forward_decls:
                # BUG 2: resolution of a forward declaration — not a duplicate.
                self._forward_decls.discard(fwd_key)
                self._scope.update(node.name, proc_type)
            else:
                self._define(node.name, proc_type, node.line)

            if node.body is not None:
                self._push_scope(node.name)
                self._define_params(node.params)
                self.visit(node.body)
                self._pop_scope()

    def visit_FuncDecl(self, node: FuncDecl) -> None:
        fwd_key = (id(self._scope), node.name.lower())
        rt_entry = self._scope.lookup(node.return_type)
        rt = rt_entry if isinstance(rt_entry, _Type) else T_ANY
        param_list = self._build_param_list(node.params)
        func_type = _FuncType(param_list, rt, check_arity=True)

        if node.forward:
            self._define(node.name, func_type, node.line)
            self._forward_decls.add(fwd_key)
        else:
            if fwd_key in self._forward_decls:
                # BUG 2: resolution of a forward declaration — not a duplicate.
                self._forward_decls.discard(fwd_key)
                self._scope.update(node.name, func_type)
            else:
                self._define(node.name, func_type, node.line)

            if node.body is not None:
                self._push_scope(node.name)
                # The function name is also a writable result variable inside
                self._define(node.name, rt, node.line)
                self._define_params(node.params)
                self.visit(node.body)
                self._pop_scope()

    def _build_param_list(self, params: list) -> list:
        return [
            (p.names, self._scope.lookup(p.type_name) or T_ANY, p.by_ref)
            for p in params
        ]

    def _define_params(self, params: list) -> None:
        for p in params:
            pt = self._scope.lookup(p.type_name) or T_ANY
            for nm in p.names:
                self._define(nm, pt, p.line)

    # ----------------------------------------------------------
    # Visitor — Statements
    # ----------------------------------------------------------

    def visit_CompoundStmt(self, node: CompoundStmt) -> None:
        for s in node.stmts:
            self.visit(s)

    def visit_AssignStmt(self, node: AssignStmt) -> None:
        vt = self._expr_type(node.target)
        et = self._expr_type(node.value)
        if not isinstance(vt, _AnyType) and not isinstance(et, _AnyType):
            if not self._compatible(vt, et):
                self._err('type_mismatch', node.line,
                          f"cannot assign {et} to {vt}")

    def visit_IfStmt(self, node: IfStmt) -> None:
        ct = self._expr_type(node.condition)
        if not isinstance(ct, (_BoolType, _AnyType)):
            self._err('type_mismatch', node.line,
                      f"'if' condition must be boolean, got {ct}")
        self.visit(node.then_branch)
        self.visit(node.else_branch)

    def visit_WhileStmt(self, node: WhileStmt) -> None:
        ct = self._expr_type(node.condition)
        if not isinstance(ct, (_BoolType, _AnyType)):
            self._err('type_mismatch', node.line,
                      f"'while' condition must be boolean, got {ct}")
        self.visit(node.body)

    def visit_ForStmt(self, node: ForStmt) -> None:
        if self._scope.lookup(node.var) is None:
            self._undeclared(node.var, node.line)
        self._expr_type(node.start)
        self._expr_type(node.end)
        self.visit(node.body)

    def visit_RepeatStmt(self, node: RepeatStmt) -> None:
        for s in node.body:
            self.visit(s)
        ct = self._expr_type(node.condition)
        if not isinstance(ct, (_BoolType, _AnyType)):
            self._err('type_mismatch', node.line,
                      f"'repeat' condition must be boolean, got {ct}")

    def visit_CaseStmt(self, node: CaseStmt) -> None:
        self._expr_type(node.expression)
        for labels, s in node.elements:
            for lbl in labels:
                self._expr_type(lbl)
            self.visit(s)

    def visit_GotoStmt(self, node: GotoStmt) -> None:
        if self._scope.lookup(str(node.label)) is None:
            self._err('undeclared_label', node.line,
                      f"label '{node.label}' is not declared")

    def visit_WritelnStmt(self, node: WritelnStmt) -> None:
        for a in node.args:
            self._expr_type(a)

    def visit_ProcCallStmt(self, node: ProcCallStmt) -> None:
        entry = self._scope.lookup(node.name)
        if entry is None:
            self._undeclared(node.name, node.line)
        for a in node.args:
            self._expr_type(a)
        # BUG 3: validate arity for user-defined procedures
        expected = self._expected_arity(entry) if entry is not None else None
        if expected is not None and len(node.args) != expected:
            self._err('arity_mismatch', node.line,
                      f"'{node.name}' expects {expected} argument(s), "
                      f"got {len(node.args)}")

    def visit_WithStmt(self, node: WithStmt) -> None:
        # BUG 5: collect record fields from all with-variables and make them
        # directly visible in the body scope.
        record_fields: Dict[str, _Type] = {}
        for v in node.vars:
            t = self._expr_type(v)
            if isinstance(t, _RecordType):
                record_fields.update(t.fields)

        self._push_scope('<with>')
        for field_name, field_type in record_fields.items():
            self._scope.define(field_name, field_type)
        self.visit(node.body)
        self._pop_scope()

    # ----------------------------------------------------------
    # Expression type inference
    # (_expr_type returns _Type directly, unlike visit_* which return None)
    # ----------------------------------------------------------

    def _expr_type(self, node: Any) -> _Type:
        """Analyse *node* as an expression and return its inferred _Type."""
        if node is None:
            return T_ANY
        if isinstance(node, IntLit):
            return T_INT
        if isinstance(node, RealLit):
            return T_REAL
        if isinstance(node, StrLit):
            return T_STR
        if isinstance(node, NilLit):
            return T_NIL
        # PROBLEMA 12: BoolLit is now a first-class literal (like NilLit)
        if isinstance(node, BoolLit):
            return T_BOOL

        if isinstance(node, Var):
            entry = self._scope.lookup(node.name)
            if entry is None:
                self._undeclared(node.name, node.line)
                return T_ANY
            return entry if isinstance(entry, _Type) else T_ANY

        if isinstance(node, IndexVar):
            base_t = self._expr_type(node.base)
            for idx in node.indices:
                self._expr_type(idx)
            if isinstance(base_t, _ArrayType):
                return base_t.element_type
            return T_ANY

        if isinstance(node, FieldVar):
            base_t = self._expr_type(node.base)
            if isinstance(base_t, _RecordType):
                ft = base_t.fields.get(node.field_name.lower())
                if ft is None:
                    self._err('undeclared_field', node.line,
                              f"record has no field '{node.field_name}'")
                    return T_ANY
                return ft
            return T_ANY

        if isinstance(node, DerefVar):
            base_t = self._expr_type(node.base)
            if isinstance(base_t, _PointerType):
                resolved = self._scope.lookup(base_t.target_name)
                if isinstance(resolved, _Type):
                    return resolved
            elif not isinstance(base_t, _AnyType):
                self._err('type_mismatch', node.line,
                          f"cannot dereference non-pointer type {base_t}")
            return T_ANY

        if isinstance(node, UnaryOp):
            ot = self._expr_type(node.operand)
            if node.op in ('PLUS', 'MINUS'):
                return ot
            if node.op == 'NOT':
                if not isinstance(ot, (_BoolType, _AnyType)):
                    self._err('type_mismatch', node.line,
                              f"'NOT' operator requires a boolean operand, "
                              f"got {ot}")
                return T_BOOL
            return T_ANY

        if isinstance(node, BinOp):
            lt = self._expr_type(node.left)
            rt = self._expr_type(node.right)
            op = node.op
            if op in ('AND', 'OR'):
                if not isinstance(lt, (_BoolType, _AnyType)):
                    self._err('type_mismatch', node.line,
                              f"'{op}' operator requires boolean operands, "
                              f"left operand is {lt}")
                if not isinstance(rt, (_BoolType, _AnyType)):
                    self._err('type_mismatch', node.line,
                              f"'{op}' operator requires boolean operands, "
                              f"right operand is {rt}")
                return T_BOOL
            if op in ('EQUALS', 'NEQ', 'LT', 'GT', 'LEQ', 'GEQ', 'IN'):
                return T_BOOL
            if op in ('PLUS', 'MINUS', 'TIMES'):
                if isinstance(lt, _RealType) or isinstance(rt, _RealType):
                    return T_REAL
                return T_INT
            if op == 'DIVIDE':
                return T_REAL
            if op in ('DIV', 'MOD'):
                return T_INT
            return T_ANY

        if isinstance(node, FuncCall):
            entry = self._scope.lookup(node.name)
            if entry is None:
                self._undeclared(node.name, node.line)
            for arg in node.args:
                self._expr_type(arg)
            # BUG 3: validate arity for user-defined functions
            if entry is not None:
                expected = self._expected_arity(entry)
                if expected is not None and len(node.args) != expected:
                    self._err('arity_mismatch', node.line,
                              f"'{node.name}' expects {expected} argument(s), "
                              f"got {len(node.args)}")
            if isinstance(entry, _FuncType):
                return entry.return_type
            return T_ANY

        return T_ANY


# ============================================================
# Public entry point
# ============================================================

def analyze(program: Program) -> SemanticResult:
    """
    Run semantic analysis on a parsed Mini-Pascal *program* AST.

    Returns a :class:`SemanticResult` containing any errors found.
    """
    return SemanticAnalyzer().visit(program)
