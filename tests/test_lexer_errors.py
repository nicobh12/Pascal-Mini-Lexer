"""Error-detection tests for the Mini-Pascal PLY lexer.

Covers:
- Illegal characters  (t_error)
- Unterminated string literals
- Unterminated brace comments  { ...
- Unterminated paren-star comments  (* ...
- Invalid tokens  (digits immediately followed by letters, e.g. 2wex)
- Error recovery  (valid tokens produced after an error)
- LexError attributes  (kind, line, value)
- Multiple errors in a single input
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import mini_pascal_lex as lexer_module
from mini_pascal_lex import LexError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def tokenize_errors(source: str) -> tuple[list[tuple[str, object]], list[LexError]]:
    """Return (tokens, errors) produced by scanning *source*."""
    lx = lexer_module.make_lexer()
    lx.input(source)
    tokens = [(tok.type, tok.value) for tok in lx]
    return tokens, lx.errors


# ---------------------------------------------------------------------------
# Illegal characters
# ---------------------------------------------------------------------------
class TestIllegalCharacters:
    def test_hash_produces_error(self):
        _, errors = tokenize_errors('#')
        assert len(errors) == 1
        assert errors[0].kind == 'illegal_character'

    def test_dollar_produces_error(self):
        _, errors = tokenize_errors('$')
        assert len(errors) == 1
        assert errors[0].kind == 'illegal_character'

    def test_percent_produces_error(self):
        _, errors = tokenize_errors('%')
        assert len(errors) == 1
        assert errors[0].kind == 'illegal_character'

    def test_exclamation_produces_error(self):
        _, errors = tokenize_errors('!')
        assert len(errors) == 1
        assert errors[0].kind == 'illegal_character'

    def test_tilde_produces_error(self):
        _, errors = tokenize_errors('~')
        assert len(errors) == 1
        assert errors[0].kind == 'illegal_character'

    def test_backtick_produces_error(self):
        _, errors = tokenize_errors('`')
        assert len(errors) == 1
        assert errors[0].kind == 'illegal_character'

    def test_error_value_is_the_bad_char(self):
        _, errors = tokenize_errors('#')
        assert errors[0].value == '#'

    def test_error_line_number(self):
        _, errors = tokenize_errors('x\n#')
        assert errors[0].line == 2

    def test_multiple_illegal_chars(self):
        _, errors = tokenize_errors('# $ %')
        assert len(errors) == 3
        assert [e.value for e in errors] == ['#', '$', '%']

    def test_valid_tokens_still_produced_after_illegal_char(self):
        tokens, errors = tokenize_errors('#x := 1;')
        assert len(errors) == 1
        types = [t for t, _ in tokens]
        assert types == ['ID', 'ASSIGN', 'INTEGER', 'SEMICOLON']

    def test_illegal_char_between_valid_tokens(self):
        tokens, errors = tokenize_errors('x # y')
        assert len(errors) == 1
        assert [t for t, _ in tokens] == ['ID', 'ID']


# ---------------------------------------------------------------------------
# Unterminated string literals
# ---------------------------------------------------------------------------
class TestUnterminatedString:
    def test_basic_unterminated_string(self):
        tokens, errors = tokenize_errors("'hello")
        assert len(errors) == 1
        assert errors[0].kind == 'unterminated_string'

    def test_unterminated_string_no_token_produced(self):
        tokens, errors = tokenize_errors("'hello")
        assert tokens == []

    def test_unterminated_string_value_starts_with_quote(self):
        _, errors = tokenize_errors("'hello")
        assert errors[0].value.startswith("'")

    def test_unterminated_string_at_end_of_line(self):
        tokens, errors = tokenize_errors("'hello\nx := 1;")
        assert len(errors) == 1
        assert errors[0].kind == 'unterminated_string'
        # tokens from the next line must still be produced
        types = [t for t, _ in tokens]
        assert types == ['ID', 'ASSIGN', 'INTEGER', 'SEMICOLON']

    def test_unterminated_string_line_number(self):
        _, errors = tokenize_errors("x\n'oops")
        assert errors[0].line == 2

    def test_terminated_string_produces_no_error(self):
        _, errors = tokenize_errors("'hello'")
        assert errors == []

    def test_empty_string_no_error(self):
        _, errors = tokenize_errors("''")
        assert errors == []

    def test_string_with_escaped_quote_no_error(self):
        _, errors = tokenize_errors("'it''s fine'")
        assert errors == []

    def test_unterminated_after_escaped_quote(self):
        # 'it'' — the '' is an escaped quote but the string is never closed
        _, errors = tokenize_errors("'it''")
        assert len(errors) == 1
        assert errors[0].kind == 'unterminated_string'


# ---------------------------------------------------------------------------
# Unterminated brace comments
# ---------------------------------------------------------------------------
class TestUnterminatedBraceComment:
    def test_unterminated_brace_comment(self):
        _, errors = tokenize_errors('{ this comment never closes')
        assert len(errors) == 1
        assert errors[0].kind == 'unterminated_comment'

    def test_unterminated_brace_no_token_produced(self):
        tokens, _ = tokenize_errors('{ unclosed')
        assert tokens == []

    def test_terminated_brace_comment_no_error(self):
        _, errors = tokenize_errors('{ properly closed }')
        assert errors == []

    def test_tokens_after_unterminated_brace_comment(self):
        # Because the unterminated rule consumes to \Z, tokens before it are fine
        tokens, errors = tokenize_errors('x := 1; { unclosed')
        assert len(errors) == 1
        types = [t for t, _ in tokens]
        assert types == ['ID', 'ASSIGN', 'INTEGER', 'SEMICOLON']

    def test_unterminated_brace_error_value(self):
        _, errors = tokenize_errors('{ oops')
        assert errors[0].value.startswith('{')

    def test_multiline_terminated_brace_no_error(self):
        _, errors = tokenize_errors('{\n  multi-line\n  comment\n}')
        assert errors == []


# ---------------------------------------------------------------------------
# Unterminated paren-star comments
# ---------------------------------------------------------------------------
class TestUnterminatedParenComment:
    def test_unterminated_paren_comment(self):
        _, errors = tokenize_errors('(* this comment never closes')
        assert len(errors) == 1
        assert errors[0].kind == 'unterminated_comment'

    def test_unterminated_paren_no_token_produced(self):
        tokens, _ = tokenize_errors('(* unclosed')
        assert tokens == []

    def test_terminated_paren_comment_no_error(self):
        _, errors = tokenize_errors('(* properly closed *)')
        assert errors == []

    def test_tokens_before_unterminated_paren_comment(self):
        tokens, errors = tokenize_errors('x := 1; (* unclosed')
        assert len(errors) == 1
        types = [t for t, _ in tokens]
        assert types == ['ID', 'ASSIGN', 'INTEGER', 'SEMICOLON']

    def test_unterminated_paren_error_value(self):
        _, errors = tokenize_errors('(* oops')
        assert errors[0].value.startswith('(*')

    def test_multiline_terminated_paren_no_error(self):
        _, errors = tokenize_errors('(*\n  multi-line\n  comment\n*)')
        assert errors == []

    def test_unterminated_paren_multiline(self):
        _, errors = tokenize_errors('(*\n  never\n  closed')
        assert len(errors) == 1
        assert errors[0].kind == 'unterminated_comment'


# ---------------------------------------------------------------------------
# Invalid tokens  (digits immediately followed by letters)
# ---------------------------------------------------------------------------
class TestInvalidToken:
    def test_digit_followed_by_letters(self):
        _, errors = tokenize_errors('2wex')
        assert len(errors) == 1
        assert errors[0].kind == 'invalid_token'

    def test_invalid_token_value(self):
        _, errors = tokenize_errors('2wex')
        assert errors[0].value == '2wex'

    def test_invalid_token_no_tokens_produced(self):
        tokens, _ = tokenize_errors('2wex')
        assert tokens == []

    def test_multiple_digits_then_letters(self):
        _, errors = tokenize_errors('123abc')
        assert len(errors) == 1
        assert errors[0].kind == 'invalid_token'
        assert errors[0].value == '123abc'

    def test_invalid_exponent_no_digits(self):
        # '1e' looks like scientific notation but has no digits after e
        _, errors = tokenize_errors('1e')
        assert len(errors) == 1
        assert errors[0].kind == 'invalid_token'

    def test_valid_scientific_notation_no_error(self):
        _, errors = tokenize_errors('9E8')
        assert errors == []

    def test_valid_scientific_signed_no_error(self):
        _, errors = tokenize_errors('1e-3')
        assert errors == []

    def test_valid_scientific_plus_no_error(self):
        _, errors = tokenize_errors('1E+10')
        assert errors == []

    def test_invalid_token_line_number(self):
        _, errors = tokenize_errors('x\n2wex')
        assert errors[0].line == 2

    def test_recovery_after_invalid_token(self):
        tokens, errors = tokenize_errors('2wex + 1')
        assert len(errors) == 1
        types = [t for t, _ in tokens]
        assert types == ['PLUS', 'INTEGER']

    def test_invalid_token_in_declaration(self):
        # mirrors the sample: '2wex, y : integer;'
        tokens, errors = tokenize_errors('2wex, y : integer;')
        assert len(errors) == 1
        assert errors[0].kind == 'invalid_token'
        types = [t for t, _ in tokens]
        assert 'COMMA' in types
        assert 'SEMICOLON' in types


# ---------------------------------------------------------------------------
# LexError attributes
# ---------------------------------------------------------------------------
class TestLexErrorAttributes:
    def test_illegal_char_kind(self):
        _, errors = tokenize_errors('#')
        assert errors[0].kind == 'illegal_character'

    def test_unterminated_string_kind(self):
        _, errors = tokenize_errors("'oops")
        assert errors[0].kind == 'unterminated_string'

    def test_unterminated_brace_kind(self):
        _, errors = tokenize_errors('{ oops')
        assert errors[0].kind == 'unterminated_comment'

    def test_unterminated_paren_kind(self):
        _, errors = tokenize_errors('(* oops')
        assert errors[0].kind == 'unterminated_comment'

    def test_invalid_token_kind(self):
        _, errors = tokenize_errors('2wex')
        assert errors[0].kind == 'invalid_token'

    def test_lexerror_str_contains_kind(self):
        _, errors = tokenize_errors('#')
        assert 'illegal_character' in str(errors[0])

    def test_lexerror_str_contains_line(self):
        _, errors = tokenize_errors('#')
        assert '1' in str(errors[0])

    def test_lexerror_is_dataclass(self):
        _, errors = tokenize_errors('#')
        e = errors[0]
        assert hasattr(e, 'kind') and hasattr(e, 'line') and hasattr(e, 'value')


# ---------------------------------------------------------------------------
# Error recovery
# ---------------------------------------------------------------------------
class TestErrorRecovery:
    def test_lexing_continues_after_illegal_char(self):
        tokens, errors = tokenize_errors('begin # end')
        assert len(errors) == 1
        types = [t for t, _ in tokens]
        assert 'BEGIN' in types
        assert 'END' in types

    def test_lexing_continues_after_unterminated_string(self):
        tokens, errors = tokenize_errors("'bad\nx := 5;")
        assert len(errors) >= 1
        types = [t for t, _ in tokens]
        assert 'ASSIGN' in types

    def test_multiple_errors_all_collected(self):
        _, errors = tokenize_errors("# $ %")
        assert len(errors) == 3

    def test_mixed_error_types(self):
        src = "# 'unterminated\nx := { unclosed"
        _, errors = tokenize_errors(src)
        kinds = {e.kind for e in errors}
        assert 'illegal_character' in kinds
        assert 'unterminated_string' in kinds
        assert 'unterminated_comment' in kinds

    def test_valid_input_has_empty_error_list(self):
        _, errors = tokenize_errors('x := 42;')
        assert errors == []

    def test_valid_program_has_no_errors(self):
        src = "program Test;\nvar x: integer;\nbegin\n  x := 1;\nend."
        _, errors = tokenize_errors(src)
        assert errors == []

    def test_error_line_tracking_across_newlines(self):
        src = "x\ny\n#"
        _, errors = tokenize_errors(src)
        assert errors[0].line == 3
