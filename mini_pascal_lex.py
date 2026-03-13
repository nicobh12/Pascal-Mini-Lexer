# Analizador léxico para Mini-Pascal usando PLY (Python Lex-Yacc)
import ply.lex as lex

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
    r'\{[^}]*\}'
    t.lexer.lineno += t.value.count('\n')


def t_COMMENT_PAREN(t):
    r'\(\*(.|\n)*?\*\)'
    t.lexer.lineno += t.value.count('\n')


# ---------------------------------------------------------------------------
# Literal rules (functions take priority over string rules in PLY)
# ---------------------------------------------------------------------------
def t_REAL(t):
    r'\d+\.\d+([eE][+-]?\d+)?|\d+[eE][+-]?\d+'
    t.value = float(t.value)
    return t


def t_INTEGER(t):
    r'\d+'
    t.value = int(t.value)
    return t


def t_STRING(t):
    r"'([^'\n]|'')*'"
    # Strip surrounding quotes and unescape doubled single-quotes
    t.value = t.value[1:-1].replace("''", "'")
    return t


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    # Pascal is case-insensitive for keywords
    t.type = reserved.get(t.value.lower(), 'ID')
    return t


def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


def t_error(t):
    print(f"[Lexer] Illegal character '{t.value[0]}' at line {t.lexer.lineno} — skipping.")
    t.lexer.skip(1)


# ---------------------------------------------------------------------------
# Build lexer
# ---------------------------------------------------------------------------
lexer = lex.lex()


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    sample = """\
program HelloWorld;
var
  x, y : integer;
  pi   : real;
begin
  (* assign values *)
  x  := 10;
  y  := x div 3;
  pi := 3.14159;
  { print result }
  if x > y then
    writeln('x is greater')
  else
    writeln('y is greater or equal');
end.
"""

    print("Input program:")
    print("=" * 60)
    print(sample)
    print("=" * 60)
    print(f"{'Line':<6} {'Token Type':<14} Value")
    print("-" * 60)

    lexer.input(sample)
    for tok in lexer:
        print(f"{tok.lineno:<6} {tok.type:<14} {tok.value!r}")

    print("-" * 60)
    print("Lexical analysis complete.")
