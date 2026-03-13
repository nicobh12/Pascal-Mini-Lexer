"""Unit tests for the Mini-Pascal PLY lexer."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import mini_pascal_lex as lexer_module
import ply.lex as lex


def tokenize(source: str) -> list[tuple[str, object]]:
    """Return list of (type, value) tuples for *source*, ignoring whitespace."""
    lx = lex.lex(module=lexer_module)
    lx.input(source)
    return [(tok.type, tok.value) for tok in lx]


# ---------------------------------------------------------------------------
# Literals
# ---------------------------------------------------------------------------
class TestLiterals:
    def test_integer(self):
        assert tokenize('42') == [('INTEGER', 42)]

    def test_real_dot(self):
        assert tokenize('3.14') == [('REAL', 3.14)]

    def test_real_exp(self):
        t = tokenize('9E8')
        assert t[0][0] == 'REAL'
        assert t[0][1] == pytest.approx(9e8)

    def test_real_exp_signed(self):
        t = tokenize('1.5e-3')
        assert t[0][0] == 'REAL'

    def test_string_simple(self):
        assert tokenize("'hello'") == [('STRING', 'hello')]

    def test_string_escaped_quote(self):
        assert tokenize("'it''s'") == [('STRING', "it's")]

    def test_string_empty(self):
        assert tokenize("''") == [('STRING', '')]


# ---------------------------------------------------------------------------
# Identifiers & reserved words
# ---------------------------------------------------------------------------
class TestIdentifiers:
    def test_plain_id(self):
        assert tokenize('fooBar') == [('ID', 'fooBar')]

    def test_reserved_begin(self):
        assert tokenize('begin') == [('BEGIN', 'begin')]

    def test_reserved_case_insensitive(self):
        assert tokenize('BEGIN') == [('BEGIN', 'BEGIN')]
        assert tokenize('Begin') == [('BEGIN', 'Begin')]

    def test_reserved_var(self):
        assert tokenize('var') == [('VAR', 'var')]

    def test_reserved_end(self):
        assert tokenize('end') == [('END', 'end')]

    def test_reserved_writeln(self):
        assert tokenize('writeln') == [('WRITELN', 'writeln')]

    def test_reserved_writeln_case_insensitive(self):
        assert tokenize('WRITELN') == [('WRITELN', 'WRITELN')]

    def test_id_underscore(self):
        assert tokenize('_foo') == [('ID', '_foo')]


# ---------------------------------------------------------------------------
# Operators & delimiters
# ---------------------------------------------------------------------------
class TestOperators:
    def test_assign_vs_colon(self):
        toks = tokenize(':= :')
        assert toks[0] == ('ASSIGN', ':=')
        assert toks[1] == ('COLON', ':')

    def test_dotdot_vs_dot(self):
        toks = tokenize('.. .')
        assert toks[0] == ('DOTDOT', '..')
        assert toks[1] == ('DOT', '.')

    def test_leq_vs_lt(self):
        toks = tokenize('<= <')
        assert toks[0] == ('LEQ', '<=')
        assert toks[1] == ('LT', '<')

    def test_geq_vs_gt(self):
        toks = tokenize('>= >')
        assert toks[0] == ('GEQ', '>=')
        assert toks[1] == ('GT', '>')

    def test_neq(self):
        assert tokenize('<>') == [('NEQ', '<>')]

    def test_arithmetic(self):
        toks = tokenize('+ - * /')
        assert [t for t, _ in toks] == ['PLUS', 'MINUS', 'TIMES', 'DIVIDE']


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------
class TestComments:
    def test_brace_comment(self):
        assert tokenize('{ this is a comment }') == []

    def test_paren_star_comment(self):
        assert tokenize('(* another comment *)') == []

    def test_comment_between_tokens(self):
        toks = tokenize('x { skip } y')
        assert [t for t, _ in toks] == ['ID', 'ID']

    def test_multiline_comment_lineno(self):
        # 'a' = line 1, '\n' -> line 2, comment spans line 2-3 (one \n inside),
        # '\n' after '*/' -> line 4, 'b' = line 4
        lx = lex.lex(module=lexer_module)
        lx.input('a\n(* line\ntwo *)\nb')
        toks = list(lx)
        assert toks[-1].lineno == 4


# ---------------------------------------------------------------------------
# Line number tracking
# ---------------------------------------------------------------------------
class TestLineNumbers:
    def test_lineno_increments(self):
        lx = lex.lex(module=lexer_module)
        lx.input('a\nb\nc')
        toks = list(lx)
        assert toks[0].lineno == 1
        assert toks[1].lineno == 2
        assert toks[2].lineno == 3


# ---------------------------------------------------------------------------
# Integration: small Pascal snippet
# ---------------------------------------------------------------------------
class TestIntegration:
    def test_assignment_statement(self):
        types = [t for t, _ in tokenize('x := 42;')]
        assert types == ['ID', 'ASSIGN', 'INTEGER', 'SEMICOLON']

    def test_if_then_else(self):
        src = 'if a > b then c := 1 else c := 2'
        types = [t for t, _ in tokenize(src)]
        assert types == [
            'IF', 'ID', 'GT', 'ID', 'THEN',
            'ID', 'ASSIGN', 'INTEGER',
            'ELSE',
            'ID', 'ASSIGN', 'INTEGER',
        ]

    def test_for_loop(self):
        src = 'for i := 1 to 10 do'
        types = [t for t, _ in tokenize(src)]
        assert types == ['FOR', 'ID', 'ASSIGN', 'INTEGER', 'TO', 'INTEGER', 'DO']

    def test_array_range(self):
        # 'integer' is a predefined identifier in Pascal, not a reserved keyword
        src = 'array[1..10] of integer'
        types = [t for t, _ in tokenize(src)]
        assert types == [
            'ARRAY', 'LBRACKET', 'INTEGER', 'DOTDOT', 'INTEGER', 'RBRACKET',
            'OF', 'ID'
        ]
