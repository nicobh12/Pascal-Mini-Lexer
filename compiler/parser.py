"""
compiler/parser.py
Layer 2 — Syntactic analysis for Mini-Pascal using PLY yacc.

Builds a complete AST from the token stream produced by compiler.lexer.

Public API
----------
  parse(source: str) -> ParseResult
  ParseResult, ParseError            (re-exported from compiler.ast)
  All AST node classes               (re-exported from compiler.ast)
"""
from __future__ import annotations

import sys
import threading
from typing import Any, List, Optional

import ply.yacc as yacc

from compiler.ast import (                          # noqa: F401
    Program, Block,
    ConstDef, TypeDef, VarDecl, ProcDecl, FuncDecl, Param,
    SimpleType, SubrangeType, ArrayType, RecordType, SetType, FileType,
    PointerType,
    CompoundStmt, AssignStmt, IfStmt, WhileStmt, ForStmt, RepeatStmt,
    CaseStmt, GotoStmt, WritelnStmt, ProcCallStmt, WithStmt,
    IntLit, RealLit, StrLit, NilLit, BoolLit, BinOp, UnaryOp, FuncCall,
    Var, IndexVar, FieldVar, DerefVar,
    ParseError, ParseResult,
)
from compiler.lexer import tokens, make_lexer       # noqa: F401 — tokens required by PLY


# ============================================================
# Thread-local parser state (reset on each parse() call)
# PROBLEMA 10: using threading.local() makes parse() thread-safe.
# ============================================================

_state = threading.local()
_MAX_ERRORS: int = 20   # safety cap — stops recording after this many errors


def _record_parse_error(line: int, message: str) -> None:
    """Append a ParseError to the current call's error list."""
    errors = getattr(_state, 'errors', None)
    if errors is None:
        return
    last = getattr(_state, 'last_error_line', -1)
    if line == last:
        return   # suppress duplicate-line spam
    if len(errors) >= _MAX_ERRORS:
        return   # safety cap
    _state.last_error_line = line
    errors.append(ParseError(kind='syntax_error', line=line, message=message))


# ============================================================
# Helper — build Var / IndexVar / FieldVar / DerefVar
# ============================================================

def _build_var_node(name: str, suffix_list: list, line: int = 0) -> Any:
    node: Any = Var(name=name, line=line)
    for s in suffix_list:
        kind = s[0]
        if kind == 'index':
            node = IndexVar(base=node, indices=s[1], line=line)
        elif kind == 'field':
            node = FieldVar(base=node, field_name=s[1], line=line)
        elif kind == 'deref':
            node = DerefVar(base=node, line=line)
    return node


def _bool_or_var(name: str, suffix_list: list, line: int = 0) -> Any:
    """
    Return BoolLit for the predefined Pascal constants 'true'/'false'
    (PROBLEMA 12), or a Var/IndexVar/FieldVar/DerefVar otherwise.
    """
    lo = name.lower()
    if lo in ('true', 'false') and not suffix_list:
        return BoolLit(value=(lo == 'true'), line=line)
    return _build_var_node(name, suffix_list, line)


# ============================================================
# Grammar Rules
# ============================================================

# ---- Program -----------------------------------------------

def p_program(p):
    'program : PROGRAM ID opt_prog_params SEMICOLON block DOT'
    p[0] = Program(name=p[2], params=p[3], block=p[5], line=p.lineno(1))


def p_opt_prog_params_some(p):
    'opt_prog_params : LPAREN id_list RPAREN'
    p[0] = p[2]


def p_opt_prog_params_none(p):
    'opt_prog_params : empty'
    p[0] = []


# ---- Block -------------------------------------------------

def p_block(p):
    'block : label_part const_part type_part var_part subprogram_part compound_stmt'
    p[0] = Block(
        labels=p[1], consts=p[2], types=p[3],
        vars=p[4], subprograms=p[5], body=p[6],
        line=p.lineno(1),
    )


# ---- Labels ------------------------------------------------

def p_label_part_some(p):
    'label_part : LABEL label_list SEMICOLON'
    p[0] = p[2]


def p_label_part_none(p):
    'label_part : empty'
    p[0] = []


def p_label_list_one(p):
    'label_list : label_id'
    p[0] = [p[1]]


def p_label_list_many(p):
    'label_list : label_list COMMA label_id'
    p[0] = p[1] + [p[3]]


def p_label_id_int(p):
    'label_id : INTEGER'
    p[0] = p[1]


def p_label_id_name(p):
    'label_id : ID'
    p[0] = p[1]


# ---- Constants ---------------------------------------------

def p_const_part_some(p):
    'const_part : CONST const_defs'
    p[0] = p[2]


def p_const_part_none(p):
    'const_part : empty'
    p[0] = []


def p_const_defs_one(p):
    'const_defs : const_def'
    p[0] = [p[1]] if p[1] is not None else []


def p_const_defs_many(p):
    'const_defs : const_defs const_def'
    p[0] = p[1] + ([p[2]] if p[2] is not None else [])


def p_const_def(p):
    'const_def : ID EQUALS constant SEMICOLON'
    p[0] = ConstDef(name=p[1], value=p[3], line=p.lineno(1))


def p_constant_plus(p):
    'constant : PLUS unsigned_constant'
    p[0] = UnaryOp(op='PLUS', operand=p[2], line=p.lineno(1))


def p_constant_minus(p):
    'constant : MINUS unsigned_constant'
    p[0] = UnaryOp(op='MINUS', operand=p[2], line=p.lineno(1))


def p_constant_unsigned(p):
    'constant : unsigned_constant'
    p[0] = p[1]


def p_unsigned_constant_int(p):
    'unsigned_constant : INTEGER'
    p[0] = IntLit(value=p[1], line=p.lineno(1))


def p_unsigned_constant_real(p):
    'unsigned_constant : REAL'
    p[0] = RealLit(value=p[1], line=p.lineno(1))


def p_unsigned_constant_str(p):
    'unsigned_constant : STRING'
    p[0] = StrLit(value=p[1], line=p.lineno(1))


def p_unsigned_constant_nil(p):
    'unsigned_constant : NIL'
    p[0] = NilLit(line=p.lineno(1))


def p_unsigned_constant_id(p):
    'unsigned_constant : ID'
    # PROBLEMA 12: true/false are boolean literals, not identifier references.
    lo = p[1].lower()
    if lo == 'true':
        p[0] = BoolLit(value=True, line=p.lineno(1))
    elif lo == 'false':
        p[0] = BoolLit(value=False, line=p.lineno(1))
    else:
        p[0] = Var(name=p[1], line=p.lineno(1))


# ---- Types -------------------------------------------------

def p_type_part_some(p):
    'type_part : TYPE type_defs'
    p[0] = p[2]


def p_type_part_none(p):
    'type_part : empty'
    p[0] = []


def p_type_defs_one(p):
    'type_defs : type_def'
    p[0] = [p[1]] if p[1] is not None else []


def p_type_defs_many(p):
    'type_defs : type_defs type_def'
    p[0] = p[1] + ([p[2]] if p[2] is not None else [])


def p_type_def(p):
    'type_def : ID EQUALS type_denoter SEMICOLON'
    p[0] = TypeDef(name=p[1], type_node=p[3], line=p.lineno(1))


def p_type_denoter_simple(p):
    'type_denoter : simple_type'
    p[0] = p[1]


def p_type_denoter_array(p):
    'type_denoter : array_type'
    p[0] = p[1]


def p_type_denoter_record(p):
    'type_denoter : record_type'
    p[0] = p[1]


def p_type_denoter_set(p):
    'type_denoter : set_type'
    p[0] = p[1]


def p_type_denoter_file(p):
    'type_denoter : file_type'
    p[0] = p[1]


def p_type_denoter_pointer(p):
    'type_denoter : pointer_type'
    p[0] = p[1]


def p_type_denoter_packed(p):
    'type_denoter : packed_struct'
    p[0] = p[1]


def p_pointer_type(p):
    'pointer_type : CARET ID'
    p[0] = PointerType(target=p[2], line=p.lineno(1))


def p_packed_struct_array(p):
    'packed_struct : PACKED array_type'
    p[2].packed = True
    p[0] = p[2]


def p_packed_struct_record(p):
    'packed_struct : PACKED record_type'
    p[2].packed = True
    p[0] = p[2]


def p_packed_struct_set(p):
    'packed_struct : PACKED set_type'
    p[2].packed = True
    p[0] = p[2]


def p_packed_struct_file(p):
    'packed_struct : PACKED file_type'
    p[2].packed = True
    p[0] = p[2]


# simple_type: ID listed FIRST so reduce/reduce on ';' etc. picks SimpleType
def p_simple_type_id(p):
    'simple_type : ID'
    p[0] = SimpleType(name=p[1], line=p.lineno(1))


def p_simple_type_subrange(p):
    'simple_type : constant DOTDOT constant'
    p[0] = SubrangeType(low=p[1], high=p[3], line=p.lineno(1))


def p_array_type(p):
    'array_type : ARRAY LBRACKET simple_type_list RBRACKET OF type_denoter'
    p[0] = ArrayType(indices=p[3], element_type=p[6], line=p.lineno(1))


def p_simple_type_list_one(p):
    'simple_type_list : simple_type'
    p[0] = [p[1]]


def p_simple_type_list_many(p):
    'simple_type_list : simple_type_list COMMA simple_type'
    p[0] = p[1] + [p[3]]


def p_record_type(p):
    'record_type : RECORD field_list END'
    p[0] = RecordType(fields=p[2], line=p.lineno(1))


def p_field_list_nonempty(p):
    'field_list : nonempty_field_list opt_trailing_semi'
    p[0] = p[1]


def p_field_list_empty(p):
    'field_list : empty'
    p[0] = []


def p_nonempty_field_list_one(p):
    'nonempty_field_list : record_section'
    p[0] = [p[1]]


def p_nonempty_field_list_many(p):
    'nonempty_field_list : nonempty_field_list SEMICOLON record_section'
    p[0] = p[1] + [p[3]]


def p_record_section(p):
    'record_section : id_list COLON type_denoter'
    p[0] = (p[1], p[3])


def p_set_type(p):
    'set_type : SET OF simple_type'
    p[0] = SetType(base_type=p[3], line=p.lineno(1))


def p_file_type(p):
    'file_type : FILE OF type_denoter'
    p[0] = FileType(component_type=p[3], line=p.lineno(1))


def p_opt_trailing_semi_yes(p):
    'opt_trailing_semi : SEMICOLON'
    p[0] = None


def p_opt_trailing_semi_no(p):
    'opt_trailing_semi : empty'
    p[0] = None


# ---- Var declarations --------------------------------------

def p_var_part_some(p):
    'var_part : VAR var_decl_list'
    p[0] = p[2]


def p_var_part_none(p):
    'var_part : empty'
    p[0] = []


def p_var_decl_list_one(p):
    'var_decl_list : var_decl'
    p[0] = [p[1]] if p[1] is not None else []


def p_var_decl_list_many(p):
    'var_decl_list : var_decl_list var_decl'
    p[0] = p[1] + ([p[2]] if p[2] is not None else [])


def p_var_decl(p):
    'var_decl : id_list COLON type_denoter SEMICOLON'
    p[0] = VarDecl(names=p[1], type_node=p[3], line=p.lineno(1))


# ---- ID list -----------------------------------------------

def p_id_list_one(p):
    'id_list : ID'
    p[0] = [p[1]]


def p_id_list_many(p):
    'id_list : id_list COMMA ID'
    p[0] = p[1] + [p[3]]


# ---- Subprograms -------------------------------------------

def p_subprogram_part_none(p):
    'subprogram_part : empty'
    p[0] = []


def p_subprogram_part_some(p):
    'subprogram_part : subprogram_part subprogram'
    p[0] = p[1] + [p[2]]


def p_subprogram_proc(p):
    'subprogram : procedure_decl'
    p[0] = p[1]


def p_subprogram_func(p):
    'subprogram : function_decl'
    p[0] = p[1]


def p_procedure_decl(p):
    'procedure_decl : PROCEDURE ID formal_params SEMICOLON proc_tail'
    forward, body = p[5]
    p[0] = ProcDecl(name=p[2], params=p[3], body=body,
                    forward=forward, line=p.lineno(1))


def p_proc_tail_forward(p):
    'proc_tail : FORWARD SEMICOLON'
    p[0] = (True, None)


def p_proc_tail_body(p):
    'proc_tail : block SEMICOLON'
    p[0] = (False, p[1])


def p_function_decl(p):
    'function_decl : FUNCTION ID formal_params COLON ID SEMICOLON func_tail'
    forward, body = p[7]
    p[0] = FuncDecl(name=p[2], params=p[3], return_type=p[5],
                    body=body, forward=forward, line=p.lineno(1))


def p_func_tail_forward(p):
    'func_tail : FORWARD SEMICOLON'
    p[0] = (True, None)


def p_func_tail_body(p):
    'func_tail : block SEMICOLON'
    p[0] = (False, p[1])


def p_formal_params_some(p):
    'formal_params : LPAREN param_sections RPAREN'
    p[0] = p[2]


def p_formal_params_none(p):
    'formal_params : empty'
    p[0] = []


def p_param_sections_one(p):
    'param_sections : param_section'
    p[0] = [p[1]]


def p_param_sections_many(p):
    'param_sections : param_sections SEMICOLON param_section'
    p[0] = p[1] + [p[3]]


def p_param_section_val(p):
    'param_section : id_list COLON ID'
    p[0] = Param(names=p[1], type_name=p[3], by_ref=False, line=p.lineno(1))


def p_param_section_ref(p):
    'param_section : VAR id_list COLON ID'
    p[0] = Param(names=p[2], type_name=p[4], by_ref=True, line=p.lineno(1))


# ---- Statements --------------------------------------------

def p_compound_stmt(p):
    'compound_stmt : BEGIN stmt_seq END'
    p[0] = CompoundStmt(stmts=p[2], line=p.lineno(1))


def p_stmt_seq_first(p):
    'stmt_seq : statement'
    p[0] = [p[1]] if p[1] is not None else []


def p_stmt_seq_more(p):
    'stmt_seq : stmt_seq SEMICOLON statement'
    stmts = p[1]
    if p[3] is not None:
        stmts = stmts + [p[3]]
    p[0] = stmts


# statement dispatches to id_stmt (assign or proc_call) or specialised forms
def p_statement_id(p):
    'statement : id_stmt'
    p[0] = p[1]


def p_statement_if(p):
    'statement : if_stmt'
    p[0] = p[1]


def p_statement_while(p):
    'statement : while_stmt'
    p[0] = p[1]


def p_statement_for(p):
    'statement : for_stmt'
    p[0] = p[1]


def p_statement_repeat(p):
    'statement : repeat_stmt'
    p[0] = p[1]


def p_statement_case(p):
    'statement : case_stmt'
    p[0] = p[1]


def p_statement_goto(p):
    'statement : goto_stmt'
    p[0] = p[1]


def p_statement_writeln(p):
    'statement : writeln_stmt'
    p[0] = p[1]


def p_statement_with(p):
    'statement : with_stmt'
    p[0] = p[1]


def p_statement_compound(p):
    'statement : compound_stmt'
    p[0] = p[1]


def p_statement_empty(p):
    'statement : empty'
    p[0] = None


# BUG 6: labeled statements  (10: writeln  or  exit: foo)
# PLY's default shift/reduce resolution (prefer shift) correctly handles the
# ambiguity between  id_prefix : ID var_suffix  and  statement : ID COLON statement
# when lookahead is COLON — the shift (label rule) wins, which is correct Pascal.
def p_statement_labeled_int(p):
    'statement : INTEGER COLON statement'
    p[0] = p[3]   # discard the label, keep the inner statement


def p_statement_labeled_id(p):
    'statement : ID COLON statement'
    p[0] = p[3]


# id_stmt: handles both assignment (target := expr) and procedure calls.
# Using id_prefix avoids the classic LALR(1) conflict between proc_call and
# assignment — the decision is delayed until after the prefix is consumed.

def p_id_stmt_assign(p):
    'id_stmt : id_prefix ASSIGN expression'
    p[0] = AssignStmt(target=p[1], value=p[3], line=p.lineno(2))


def p_id_stmt_call(p):
    'id_stmt : id_prefix'
    node = p[1]
    if isinstance(node, FuncCall):
        p[0] = ProcCallStmt(name=node.name, args=node.args, line=node.line)
    elif isinstance(node, Var):
        p[0] = ProcCallStmt(name=node.name, args=[], line=node.line)
    elif isinstance(node, BoolLit):
        # 'true' or 'false' used as a bare statement — not valid Pascal
        _record_parse_error(node.line,
                            "boolean literal cannot be used as a statement")
        p[0] = None
    else:
        # BUG 7: complex lvalue (a[i], pt.x, p^) used as a bare statement.
        # Emit a meaningful error with the real line number instead of the
        # bogus '?' sentinel that confuses the semantic analyser.
        line = getattr(node, 'line', p.lineno(1))
        _record_parse_error(line,
                            "expression cannot be used as a statement")
        p[0] = None


def p_id_prefix_call(p):
    'id_prefix : ID LPAREN arg_list RPAREN'
    p[0] = FuncCall(name=p[1], args=p[3], line=p.lineno(1))


def p_id_prefix_var(p):
    'id_prefix : ID var_suffix'
    # PROBLEMA 12: emit BoolLit for the predefined Pascal boolean constants.
    p[0] = _bool_or_var(p[1], p[2], line=p.lineno(1))


# ---- var (used in expressions and with_stmt) ---------------

def p_var(p):
    'var : ID var_suffix'
    # PROBLEMA 12: same BoolLit treatment in expression context.
    p[0] = _bool_or_var(p[1], p[2], line=p.lineno(1))


def p_var_suffix_empty(p):
    'var_suffix : empty'
    p[0] = []


def p_var_suffix_extend(p):
    'var_suffix : var_suffix suffix'
    p[0] = p[1] + [p[2]]


def p_suffix_index(p):
    'suffix : LBRACKET expr_list RBRACKET'
    p[0] = ('index', p[2])


def p_suffix_field(p):
    'suffix : DOT ID'
    p[0] = ('field', p[2])


def p_suffix_deref(p):
    'suffix : CARET'
    p[0] = ('deref',)


# ---- Structured statements ---------------------------------

def p_if_stmt_then(p):
    'if_stmt : IF expression THEN statement'
    p[0] = IfStmt(condition=p[2], then_branch=p[4], else_branch=None,
                  line=p.lineno(1))


def p_if_stmt_else(p):
    'if_stmt : IF expression THEN statement ELSE statement'
    p[0] = IfStmt(condition=p[2], then_branch=p[4], else_branch=p[6],
                  line=p.lineno(1))


def p_while_stmt(p):
    'while_stmt : WHILE expression DO statement'
    p[0] = WhileStmt(condition=p[2], body=p[4], line=p.lineno(1))


def p_for_stmt_to(p):
    'for_stmt : FOR ID ASSIGN expression TO expression DO statement'
    p[0] = ForStmt(var=p[2], start=p[4], direction='to', end=p[6],
                   body=p[8], line=p.lineno(1))


def p_for_stmt_downto(p):
    'for_stmt : FOR ID ASSIGN expression DOWNTO expression DO statement'
    p[0] = ForStmt(var=p[2], start=p[4], direction='downto', end=p[6],
                   body=p[8], line=p.lineno(1))


def p_repeat_stmt(p):
    'repeat_stmt : REPEAT stmt_seq UNTIL expression'
    p[0] = RepeatStmt(body=p[2], condition=p[4], line=p.lineno(1))


def p_case_stmt(p):
    'case_stmt : CASE expression OF case_elements opt_trailing_semi END'
    p[0] = CaseStmt(expression=p[2], elements=p[4], line=p.lineno(1))


def p_case_elements_one(p):
    'case_elements : case_element'
    p[0] = [p[1]] if p[1] is not None else []


def p_case_elements_more(p):
    'case_elements : case_elements SEMICOLON case_element'
    elems = p[1]
    if p[3] is not None:
        elems = elems + [p[3]]
    p[0] = elems


def p_case_element(p):
    'case_element : const_list COLON statement'
    p[0] = (p[1], p[3])


def p_case_element_empty(p):
    'case_element : empty'
    p[0] = None


def p_const_list_one(p):
    'const_list : constant'
    p[0] = [p[1]]


def p_const_list_many(p):
    'const_list : const_list COMMA constant'
    p[0] = p[1] + [p[3]]


def p_goto_stmt_int(p):
    'goto_stmt : GOTO INTEGER'
    p[0] = GotoStmt(label=p[2], line=p.lineno(1))


def p_goto_stmt_id(p):
    'goto_stmt : GOTO ID'
    p[0] = GotoStmt(label=p[2], line=p.lineno(1))


def p_writeln_stmt_noargs(p):
    'writeln_stmt : WRITELN'
    p[0] = WritelnStmt(args=[], line=p.lineno(1))


def p_writeln_stmt_args(p):
    'writeln_stmt : WRITELN LPAREN arg_list RPAREN'
    p[0] = WritelnStmt(args=p[3], line=p.lineno(1))


def p_with_stmt(p):
    'with_stmt : WITH var_list DO statement'
    p[0] = WithStmt(vars=p[2], body=p[4], line=p.lineno(1))


def p_var_list_one(p):
    'var_list : var'
    p[0] = [p[1]]


def p_var_list_many(p):
    'var_list : var_list COMMA var'
    p[0] = p[1] + [p[3]]


# ---- Expressions -------------------------------------------
# Traditional Pascal grammar: expression → simple_expr → term → factor
# Precedence is encoded in the grammar structure (no PLY %prec needed).

def p_expression_relop(p):
    'expression : simple_expr relop simple_expr'
    p[0] = BinOp(op=p[2], left=p[1], right=p[3], line=p.lineno(2))


def p_expression_simple(p):
    'expression : simple_expr'
    p[0] = p[1]


def p_relop(p):
    '''relop : EQUALS
             | NEQ
             | LT
             | GT
             | LEQ
             | GEQ
             | IN'''
    # Use token TYPE name (e.g. 'GT', 'EQUALS'), not the raw value ('>', '=')
    p[0] = p.slice[1].type


def p_simple_expr_sign_term(p):
    'simple_expr : sign term'
    p[0] = UnaryOp(op=p[1], operand=p[2], line=p.lineno(1))


def p_simple_expr_term(p):
    'simple_expr : term'
    p[0] = p[1]


def p_simple_expr_addop(p):
    'simple_expr : simple_expr addop term'
    p[0] = BinOp(op=p[2], left=p[1], right=p[3], line=p.lineno(2))


def p_sign_plus(p):
    'sign : PLUS'
    p[0] = 'PLUS'


def p_sign_minus(p):
    'sign : MINUS'
    p[0] = 'MINUS'


def p_addop_plus(p):
    'addop : PLUS'
    p[0] = 'PLUS'


def p_addop_minus(p):
    'addop : MINUS'
    p[0] = 'MINUS'


def p_addop_or(p):
    'addop : OR'
    p[0] = 'OR'


def p_term_factor(p):
    'term : factor'
    p[0] = p[1]


def p_term_mulop(p):
    'term : term mulop factor'
    p[0] = BinOp(op=p[2], left=p[1], right=p[3], line=p.lineno(2))


def p_mulop_times(p):
    'mulop : TIMES'
    p[0] = 'TIMES'


def p_mulop_divide(p):
    'mulop : DIVIDE'
    p[0] = 'DIVIDE'


def p_mulop_div(p):
    'mulop : DIV'
    p[0] = 'DIV'


def p_mulop_mod(p):
    'mulop : MOD'
    p[0] = 'MOD'


def p_mulop_and(p):
    'mulop : AND'
    p[0] = 'AND'


def p_factor_int(p):
    'factor : INTEGER'
    p[0] = IntLit(value=p[1], line=p.lineno(1))


def p_factor_real(p):
    'factor : REAL'
    p[0] = RealLit(value=p[1], line=p.lineno(1))


def p_factor_str(p):
    'factor : STRING'
    p[0] = StrLit(value=p[1], line=p.lineno(1))


def p_factor_nil(p):
    'factor : NIL'
    p[0] = NilLit(line=p.lineno(1))


def p_factor_paren(p):
    'factor : LPAREN expression RPAREN'
    p[0] = p[2]


def p_factor_not(p):
    'factor : NOT factor'
    p[0] = UnaryOp(op='NOT', operand=p[2], line=p.lineno(1))


def p_factor_funccall(p):
    'factor : ID LPAREN arg_list RPAREN'
    p[0] = FuncCall(name=p[1], args=p[3], line=p.lineno(1))


def p_factor_var(p):
    'factor : var'
    p[0] = p[1]


def p_arg_list_empty(p):
    'arg_list : empty'
    p[0] = []


def p_arg_list_one(p):
    'arg_list : expression'
    p[0] = [p[1]]


def p_arg_list_many(p):
    'arg_list : arg_list COMMA expression'
    p[0] = p[1] + [p[3]]


def p_expr_list_one(p):
    'expr_list : expression'
    p[0] = [p[1]]


def p_expr_list_many(p):
    'expr_list : expr_list COMMA expression'
    p[0] = p[1] + [p[3]]


# ---- Empty -------------------------------------------------

def p_empty(p):
    'empty :'
    p[0] = None


# ============================================================
# Error recovery productions
# ============================================================
# Strategy: two-layer recovery.
#
# Layer A — SPECIFIC rules (preferred by PLY because they match higher in the
#   LR stack without popping).  Each rule ends with `error` so PLY can shift
#   the error token immediately when the EXPECTED token is missing, leaving the
#   erroneous lookahead in place for the next production to consume.  After
#   each recovery we call p.parser.errok() to reset PLY's internal errorcount,
#   allowing the NEXT bad token to trigger a new p_error call immediately.
#
# Layer B — GENERIC `error SEMICOLON` rules (fallback for completely malformed
#   declarations / statements).  They discard tokens up to the next `;` and
#   also call errok() so subsequent errors are not suppressed.

# ---- Layer A: missing semicolon after well-formed constructs ---------------

def p_const_def_missing_semi(p):
    'const_def : ID EQUALS constant error'
    # e.g. "limit = 100" with no ";" — next token is left as lookahead
    p.parser.errok()
    p[0] = ConstDef(name=p[1], value=p[3], line=p.lineno(1))


def p_type_def_missing_semi(p):
    'type_def : ID EQUALS type_denoter error'
    p.parser.errok()
    p[0] = TypeDef(name=p[1], type_node=p[3], line=p.lineno(1))


def p_var_decl_missing_semi(p):
    'var_decl : id_list COLON type_denoter error'
    p.parser.errok()
    p[0] = VarDecl(names=p[1], type_node=p[3], line=p.lineno(1))


# ---- Layer A: missing keywords in structured statements --------------------

def p_if_stmt_missing_then(p):
    'if_stmt : IF expression error statement'
    # e.g. "if x > 0 y := 1"  (THEN absent)
    p.parser.errok()
    p[0] = IfStmt(condition=p[2], then_branch=p[4], else_branch=None,
                  line=p.lineno(1))


def p_for_stmt_to_missing_do(p):
    'for_stmt : FOR ID ASSIGN expression TO expression error statement'
    # e.g. "for i := 1 to n writeln(i)"  (DO absent)
    p.parser.errok()
    p[0] = ForStmt(var=p[2], start=p[4], direction='to', end=p[6],
                   body=p[8], line=p.lineno(1))


def p_for_stmt_downto_missing_do(p):
    'for_stmt : FOR ID ASSIGN expression DOWNTO expression error statement'
    p.parser.errok()
    p[0] = ForStmt(var=p[2], start=p[4], direction='downto', end=p[6],
                   body=p[8], line=p.lineno(1))


def p_while_stmt_missing_do(p):
    'while_stmt : WHILE expression error statement'
    # e.g. "while x > 0 x := x - 1"  (DO absent)
    p.parser.errok()
    p[0] = WhileStmt(condition=p[2], body=p[4], line=p.lineno(1))


# ---- Layer B: generic fallback productions (consume up to next ";") --------

def p_const_def_error(p):
    'const_def : error SEMICOLON'
    p.parser.errok()
    p[0] = None          # filtered out in const_defs action


def p_type_def_error(p):
    'type_def : error SEMICOLON'
    p.parser.errok()
    p[0] = None


def p_var_decl_error(p):
    'var_decl : error SEMICOLON'
    p.parser.errok()
    p[0] = None


def p_stmt_seq_missing_semi(p):
    'stmt_seq : stmt_seq error statement'
    # Two consecutive statements without ";" between them.
    # The error token fires when the parser sees a new statement start
    # where it expected SEMICOLON.  After recovery, the next error can be
    # detected immediately because errok() resets PLY's error counter.
    p.parser.errok()
    p[0] = p[1] + ([p[3]] if p[3] is not None else [])


def p_stmt_seq_error_semi(p):
    'stmt_seq : error SEMICOLON'
    p.parser.errok()
    p[0] = []


def p_id_stmt_assign_missing_expr(p):
    'id_stmt : id_prefix ASSIGN error'
    # e.g. "msg :=" with no right-hand-side expression (e.g. after an
    # unterminated string that the lexer silently discarded).
    p.parser.errok()
    p[0] = None


def p_repeat_error(p):
    'repeat_stmt : REPEAT stmt_seq error'
    p.parser.errok()
    p[0] = RepeatStmt(body=p[2], condition=NilLit(), line=p.lineno(1))


def p_error(p):
    if p is None:
        # EOF reached before the program's final ".".
        # lx.lineno is one past the last newline; subtract 1 for the actual
        # last content line.
        lx = getattr(_state, 'lexer_ref', None)
        line = max(1, lx.lineno - 1) if lx is not None else 0
        _record_parse_error(line, "unexpected end of input (missing '.'?)")
        return
    # p.value is normally a raw Python value (str/int/float), but after some
    # PLY error-recovery cycles it may arrive as a nested LexToken object.
    # Unwrap until we reach a primitive value.
    val = p.value
    while hasattr(val, 'value'):
        val = val.value
    _record_parse_error(p.lineno, f"unexpected token {val!r}")


# ============================================================
# Suppress PLY output
# ============================================================

class _NullLog:
    def warning(self, *a, **kw): pass
    def error(self, *a, **kw): pass
    def info(self, *a, **kw): pass
    def debug(self, *a, **kw): pass


# Build the LALR(1) table once at import time.
# write_tables=False prevents side-effect files during tests.
_parser = yacc.yacc(
    module=sys.modules[__name__],
    debug=False,
    write_tables=False,
    errorlog=_NullLog(),
)


# ============================================================
# Public API
# ============================================================

def parse(source: str) -> ParseResult:
    """Lex and parse *source*, returning a :class:`ParseResult`."""
    # Reset per-call thread-local state (PROBLEMA 10: thread-safe)
    _state.errors = []
    _state.last_error_line = -1
    _state.lexer_ref = None   # set below; used by p_error(None) for EOF line

    result = ParseResult()
    lexer = make_lexer()
    _state.lexer_ref = lexer  # give p_error(None) access to the current line
    lexer.input(source)

    tree = _parser.parse(source, lexer=lexer, tracking=True)

    result.program = tree
    result.lex_errors = lexer.errors
    result.parse_errors = list(_state.errors)
    return result
