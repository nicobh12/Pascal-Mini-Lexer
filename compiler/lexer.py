"""
compiler/lexer.py
Layer 1 — Lexical analysis for Mini-Pascal using PLY lex.

Public API
----------
  make_lexer() -> ply.lex.Lexer   fresh lexer with empty .errors list
  LexError                        dataclass for lexical errors
  tokens                          token-name tuple required by PLY yacc
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import List

import ply.lex as lex


# ============================================================
# Error type
# ============================================================

@dataclass
class LexError:
    """A lexical error recorded during scanning."""
    kind: str   # illegal_character | unterminated_string |
                # unterminated_comment | invalid_token
    line: int
    value: str

    def __str__(self) -> str:
        return f"[LexError] {self.kind} at line {self.line}: {self.value!r}"


def _record_error(lx: lex.Lexer, kind: str, value: str) -> None:
    if not hasattr(lx, 'errors'):
        lx.errors: List[LexError] = []
    lx.errors.append(LexError(kind=kind, line=lx.lineno, value=value))


# ============================================================
# Reserved words (case-insensitive)
# ============================================================

reserved = {
    'and': 'AND', 'array': 'ARRAY', 'begin': 'BEGIN', 'case': 'CASE',
    'const': 'CONST', 'div': 'DIV', 'do': 'DO', 'downto': 'DOWNTO',
    'else': 'ELSE', 'end': 'END', 'file': 'FILE', 'for': 'FOR',
    'forward': 'FORWARD', 'function': 'FUNCTION', 'goto': 'GOTO',
    'if': 'IF', 'in': 'IN', 'label': 'LABEL',
    'mod': 'MOD', 'nil': 'NIL', 'not': 'NOT', 'of': 'OF', 'or': 'OR',
    'packed': 'PACKED', 'procedure': 'PROCEDURE', 'program': 'PROGRAM',
    'record': 'RECORD', 'repeat': 'REPEAT', 'set': 'SET', 'then': 'THEN',
    'to': 'TO', 'type': 'TYPE', 'until': 'UNTIL', 'var': 'VAR',
    'while': 'WHILE', 'with': 'WITH', 'writeln': 'WRITELN',
}

# ============================================================
# Token list (PLY requires this name)
# ============================================================

tokens: tuple = (
    'INTEGER', 'REAL', 'STRING', 'ID',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE',
    'EQUALS', 'NEQ', 'LT', 'GT', 'LEQ', 'GEQ',
    'LPAREN', 'RPAREN', 'LBRACKET', 'RBRACKET',
    'DOTDOT', 'DOT', 'COMMA', 'ASSIGN', 'COLON', 'SEMICOLON',
    'CARET', 'AT',
) + tuple(reserved.values())

# ============================================================
# Simple (string) token rules
# ============================================================

t_PLUS      = r'\+'
t_MINUS     = r'-'
t_TIMES     = r'\*'
t_DIVIDE    = r'/'
t_EQUALS    = r'='
t_NEQ       = r'<>'
t_LEQ       = r'<='
t_GEQ       = r'>='
t_LT        = r'<'
t_GT        = r'>'
t_LBRACKET  = r'\['
t_RBRACKET  = r'\]'
t_DOTDOT    = r'\.\.'
t_DOT       = r'\.'
t_COMMA     = r','
t_ASSIGN    = r':='
t_COLON     = r':'
t_SEMICOLON = r';'
t_LPAREN    = r'\('
t_RPAREN    = r'\)'
t_CARET     = r'\^'
t_AT        = r'@'
t_ignore    = ' \t\r'

# ============================================================
# Complex token rules (functions, in match-priority order)
# ============================================================

def t_COMMENT_BRACE(t):
    r'\{[^}]*(?:\}|\Z)'
    if not t.value.endswith('}'):
        _record_error(t.lexer, 'unterminated_comment', t.value[:60])
    t.lexer.lineno += t.value.count('\n')


def t_COMMENT_PAREN(t):
    r'\(\*(.|\n)*?(?:\*\)|\Z)'
    if not t.value.endswith('*)'):
        _record_error(t.lexer, 'unterminated_comment', t.value[:60])
    t.lexer.lineno += t.value.count('\n')


_REAL_VALIDATE = re.compile(
    r'(\d+\.\d+([eE][+-]?\d+)?|\d+[eE][+-]?\d+)$'
)


def t_REAL(t):
    r'\d+\.\d+([eE][+-]?\d+)?|\d+[eE][+-]?\d+|\d+[a-zA-Z_][a-zA-Z0-9_]*'
    if _REAL_VALIDATE.match(t.value):
        t.value = float(t.value)
        return t
    _record_error(t.lexer, 'invalid_token', t.value)


def t_INTEGER(t):
    r'\d+'
    t.value = int(t.value)
    return t


_PROPER_STRING_RE = re.compile(r"'([^'\n]|'')*'$")


def t_STRING(t):
    r"'([^'\n]|'')*(?:'|(?=\n|\Z))"
    if _PROPER_STRING_RE.match(t.value):
        t.value = t.value[1:-1].replace("''", "'")
        return t
    _record_error(t.lexer, 'unterminated_string', t.value)


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value.lower(), 'ID')
    return t


def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


def t_error(t):
    _record_error(t.lexer, 'illegal_character', t.value[0])
    t.lexer.skip(1)


# ============================================================
# Public factory
# ============================================================

def make_lexer() -> lex.Lexer:
    """Return a fresh PLY lexer instance with an empty .errors list."""
    lx = lex.lex(module=sys.modules[__name__], errorlog=_NullLog())
    lx.errors: List[LexError] = []
    return lx


class _NullLog:
    def warning(self, *a, **kw): pass
    def error(self, *a, **kw): pass
    def info(self, *a, **kw): pass
    def debug(self, *a, **kw): pass
