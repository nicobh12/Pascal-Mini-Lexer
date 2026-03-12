#Analizador léxico para Mini-Pascal usando PLY (Python Lex-Yacc)
import ply.lex as lex

reserved = {
    'and': 'AND',
    'array': 'ARRAY',
    'begin': 'BEGIN',
    'case': 'CASE',
    'const': 'CONST',
    'div': 'DIV',
    'do': 'DO',
    'downto': 'DOWNTO',
    'else': 'ELSE',
    'file': 'FILE',
    'for': 'FOR',
    'forward': 'FORWARD',
    'function': 'FUNCTION',
    'goto': 'GOTO',
    'if': 'IF',
    'in': 'IN',
    'label': 'LABEL',
    'main': 'MAIN',
    'mod': 'MOD',
    'nil': 'NIL',
    'not': 'NOT',
    'of': 'OF',
    'or': 'OR',
    'packed': 'PACKED',
    'procedure': 'PROCEDURE',
    'program': 'PROGRAM',
    'record': 'RECORD',
    'repeat': 'REPEAT',
    'set': 'SET',
    'then': 'THEN',
    'to': 'TO',
    'type': 'TYPE',
    'until': 'UNTIL',
    'var': 'VAR',
    'while': 'WHILE',
    'with': 'WITH'
}

tokens: tuple[str, ...] = (
    #Standard Symbols
    'NUMBER',
    'ID',
    'PLUS',
    'MINUS',
    'TIMES',
    'DIVIDE',
    'EQUALS',
    'LT',
    'GT',
    'LBRACKET',
    'RBRACKET',
    'DOT',
    'COMMA',
    'ASSIGN',
    'COLON',
    'SEMICOLON',
    'LPAREN',
    'RPAREN',
    'NEQ',
    'LEQ',
    'GEQ',

    #Non-Standard Symbols
    'BITWISE_NOT',
    'BITWISE_AND',
    'BITWISE_OR',
    'HASH',

    'DOLLAR',
    'UNDERSCORE'
) + tuple(reserved.values())

t_PLUS   = r'\+'
t_MINUS  = r'-'
t_TIMES  = r'\*'
t_DIVIDE = r'/'
t_EQUALS = r'='
t_LT     = r'<'
t_GT     = r'>'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_DOT    = r'\.'
t_COMMA  = r','
t_ASSIGN = r':='
t_COLON  = r':'
t_SEMICOLON = r';'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_NEQ    = r'<>'
t_LEQ    = r'<='
t_GEQ    = r'>='
t_BITWISE_NOT = r'~'
t_BITWISE_AND = r'&'
t_BITWISE_OR  = r'\||!'
t_HASH = r'#'
t_DOLLAR = r'\$'
t_UNDERSCORE = r'_'

t_ignore = ' \t'

def t_NUMBER(t):
    r'(-?)(\d+\.\d+|\d+)([eE][+-]?\d+)?'
    t.value = float(t.value)
    return t

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_$]*'
    t.type = reserved.get(t.value, 'ID')
    return t


def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print(f"[Lexer] Illegal character '{t.value[0]}' at line {t.lexer.lineno} — skipping.")
    t.lexer.skip(1)

lexer = lex.lex()

if __name__ == '__main__':
    test_expression = '3.14 * 9E8 - 8 / 2'

    print(f"Input  : {test_expression!r}")
    print("-" * 50)
    print(f"{'Token Type':<12} {'Value'}")
    print("-" * 50)

    lexer.input(test_expression)

    for tok in lexer:
        print(f"{tok.type:<12} {tok.value}")

    print("-" * 50)
    print("Lexical analysis complete.")