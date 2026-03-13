# Analizador léxico para Mini-Pascal usando PLY (Python Lex-Yacc)
import re
import sys
from dataclasses import dataclass

import ply.lex as lex


# ---------------------------------------------------------------------------
# Error reporting
# ---------------------------------------------------------------------------
@dataclass
class LexError:
    """A lexical error recorded during scanning."""
    kind: str   # 'illegal_character' | 'unterminated_string' | 'unterminated_comment' | 'invalid_token'
    line: int
    value: str

    def __str__(self) -> str:
        return f"[LexError] {self.kind} at line {self.line}: {self.value!r}"


def _record_error(lx, kind: str, value: str) -> None:
    """Append a LexError to the lexer's error list (initialised lazily)."""
    if not hasattr(lx, 'errors'):
        lx.errors: list[LexError] = []
    lx.errors.append(LexError(kind=kind, line=lx.lineno, value=value))

# ---------------------------------------------------------------------------
# Reserved words (case-insensitive — matched via t_ID lowercase normalization)
# ---------------------------------------------------------------------------
reserved = {
    'and':       'AND',
    'array':     'ARRAY',
    'begin':     'BEGIN',
    'case':      'CASE',
    'const':     'CONST',
    'div':       'DIV',
    'do':        'DO',
    'downto':    'DOWNTO',
    'else':      'ELSE',
    'end':       'END',
    'file':      'FILE',
    'for':       'FOR',
    'forward':   'FORWARD',
    'function':  'FUNCTION',
    'goto':      'GOTO',
    'if':        'IF',
    'in':        'IN',
    'label':     'LABEL',
    'main':      'MAIN',
    'mod':       'MOD',
    'nil':       'NIL',
    'not':       'NOT',
    'of':        'OF',
    'or':        'OR',
    'packed':    'PACKED',
    'procedure': 'PROCEDURE',
    'program':   'PROGRAM',
    'record':    'RECORD',
    'repeat':    'REPEAT',
    'set':       'SET',
    'then':      'THEN',
    'to':        'TO',
    'type':      'TYPE',
    'until':     'UNTIL',
    'var':       'VAR',
    'while':     'WHILE',
    'with':      'WITH',
    'writeln':   'WRITELN',
}

# ---------------------------------------------------------------------------
# Token list
# ---------------------------------------------------------------------------
tokens: tuple[str, ...] = (
    # Literals
    'INTEGER',
    'REAL',
    'STRING',
    'ID',

    # Arithmetic operators
    'PLUS',
    'MINUS',
    'TIMES',
    'DIVIDE',

    # Relational operators
    'EQUALS',
    'NEQ',
    'LT',
    'GT',
    'LEQ',
    'GEQ',

    # Delimiters
    'LPAREN',
    'RPAREN',
    'LBRACKET',
    'RBRACKET',
    'DOTDOT',
    'DOT',
    'COMMA',
    'ASSIGN',
    'COLON',
    'SEMICOLON',
    'CARET',
    'AT',
) + tuple(reserved.values())

# ---------------------------------------------------------------------------
# Simple token rules (PLY sorts these by decreasing pattern length,
# so multi-char tokens like ':=' always match before ':')
# ---------------------------------------------------------------------------
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

t_ignore = ' \t\r'

# ---------------------------------------------------------------------------
# Comment rules (discarded — no return)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Literal rules (functions take priority over string rules in PLY)
# ---------------------------------------------------------------------------

# Validates that a matched value is truly a REAL literal (not e.g. '2wex').
_REAL_VALIDATE = re.compile(r'(\d+\.\d+([eE][+-]?\d+)?|\d+[eE][+-]?\d+)$')


def t_REAL(t):
    r'\d+\.\d+([eE][+-]?\d+)?|\d+[eE][+-]?\d+|\d+[a-zA-Z_][a-zA-Z0-9_]*'
    # The third alternative catches digits immediately followed by letters.
    # Valid scientific notation is handled by the first two alternatives, which
    # take precedence in the regex.  If we still end up here with something
    # like '2wex' or '1e', it is an invalid token.
    if _REAL_VALIDATE.match(t.value):
        t.value = float(t.value)
        return t
    _record_error(t.lexer, 'invalid_token', t.value)


def t_INTEGER(t):
    r'\d+'
    t.value = int(t.value)
    return t


# Matches a properly-closed Pascal string; used to validate inside t_STRING.
_PROPER_STRING_RE = re.compile(r"'([^'\n]|'')*'$")


def t_STRING(t):
    r"'([^'\n]|'')*(?:'|(?=\n|\Z))"
    if _PROPER_STRING_RE.match(t.value):
        # Strip surrounding quotes and unescape doubled single-quotes
        t.value = t.value[1:-1].replace("''", "'")
        return t
    # String opened but never closed on this line — consume and record error.
    _record_error(t.lexer, 'unterminated_string', t.value)


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    # Pascal is case-insensitive for keywords
    t.type = reserved.get(t.value.lower(), 'ID')
    return t


def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


def t_error(t):
    _record_error(t.lexer, 'illegal_character', t.value[0])
    print(f"[Lexer] Illegal character '{t.value[0]}' at line {t.lexer.lineno} — skipping.")
    t.lexer.skip(1)


# ---------------------------------------------------------------------------
# Build lexer
# ---------------------------------------------------------------------------
def make_lexer() -> lex.Lexer:
    """Create a fresh lexer instance with an empty error list."""
    lx = lex.lex(module=sys.modules[__name__])
    lx.errors: list[LexError] = []
    return lx


lexer = make_lexer()


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    sample = """\
program HelloWorld;
var
  2wex, y : integer;
  pi   : real;
begin
  (* assign values *)
  x  := 10;
  y  := x div 3 # invalid char;
  pi := 3.14159;
  { print result }
  if x > y then
    writeln('x is greater)
  else
    writeln('y is greater or equal');
end.
"""

    print("Input program:")
    print("=" * 60)
    print(sample)
    print("=" * 60)

    # --- Token table ---
    print(f"{'Line':<6} {'Token Type':<14} Value")
    print("-" * 60)

    lx = make_lexer()
    lx.input(sample)
    for tok in lx:
        print(f"{tok.lineno:<6} {tok.type:<14} {tok.value!r}")

    print("-" * 60)

    # --- Lexical errors table ---
    print()
    print("=" * 60)
    if lx.errors:
        print(f"LEXICAL ERRORS ({len(lx.errors)})")
        print("-" * 60)
        print(f"{'Line':<6} {'Kind':<25} Value")
        print("-" * 60)
        for err in lx.errors:
            print(f"{err.line:<6} {err.kind:<25} {err.value!r}")
        print("-" * 60)
    else:
        print("No lexical errors detected.")

    print("Lexical analysis complete.")
