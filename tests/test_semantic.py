"""
test_semantic.py
Exhaustive test suite for the Mini-Pascal semantic analyser.

Tests are organised by kind of semantic check performed.
"""
import unittest
from mini_pascal_parser import parse
from mini_pascal_semantic import analyze, SemanticResult, SemanticError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def prog(body: str = '', decls: str = '') -> str:
    return f"program Test;\n{decls}begin\n{body}\nend.\n"


def ok(source: str) -> SemanticResult:
    pr = parse(source)
    assert not pr.parse_errors, f"Unexpected parse errors: {pr.parse_errors}"
    return analyze(pr.program)


def err(source: str) -> SemanticResult:
    pr = parse(source)
    if pr.parse_errors:
        # Semantic analysis is skipped when there are parse errors;
        # these tests are for semantic-only failures.
        raise AssertionError(f"Source has parse errors: {pr.parse_errors}")
    return analyze(pr.program)


def has_error(result: SemanticResult, kind: str) -> bool:
    return any(e.kind == kind for e in result.errors)


# ---------------------------------------------------------------------------
# 1. Valid programs — no semantic errors
# ---------------------------------------------------------------------------

class TestValidPrograms(unittest.TestCase):

    def test_hello_world(self):
        src = "program Hello;\nbegin\n  writeln('Hello, World!')\nend.\n"
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_var_declare_use(self):
        r = ok(prog('x := 1', decls='var x: integer;\n'))
        self.assertTrue(r.ok, r.errors)

    def test_multiple_vars(self):
        r = ok(prog('x := 1;\ny := 2.0', decls='var x: integer;\n    y: real;\n'))
        self.assertTrue(r.ok, r.errors)

    def test_const_use(self):
        r = ok(prog('x := maxn', decls='const maxn = 100;\nvar x: integer;\n'))
        self.assertTrue(r.ok, r.errors)

    def test_type_alias(self):
        r = ok(prog('x := 1', decls='type myint = integer;\nvar x: myint;\n'))
        self.assertTrue(r.ok, r.errors)

    def test_procedure_call(self):
        src = prog(
            decls='procedure greet;\nbegin\n  writeln\nend;\n',
            body='greet'
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_function_call_in_expr(self):
        src = prog(
            decls=(
                'var n: integer;\n'
                'function double(x: integer): integer;\n'
                'begin\n  double := x * 2\nend;\n'
            ),
            body='n := double(5)'
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_nested_scopes(self):
        src = prog(
            decls=(
                'var g: integer;\n'
                'procedure inner;\n'
                'var local: integer;\n'
                'begin\n  local := g\nend;\n'
            ),
            body='g := 1'
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_array_access(self):
        src = prog(
            decls='var a: array[1..10] of integer;\n    i: integer;\n',
            body='a[i] := 0'
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_record_field_access(self):
        src = prog(
            decls=(
                'type point = record x: real; y: real end;\n'
                'var p: point;\n'
            ),
            body='p.x := 1.0'
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_int_to_real_assignment(self):
        r = ok(prog('x := 1', decls='var x: real;\n'))
        self.assertTrue(r.ok, r.errors)

    def test_for_loop(self):
        r = ok(prog(
            decls='var i, s: integer;\n',
            body='for i := 1 to 10 do s := s + i'
        ))
        self.assertTrue(r.ok, r.errors)

    def test_while_loop(self):
        r = ok(prog(
            decls='var i: integer;\n',
            body='while i < 10 do i := i + 1'
        ))
        self.assertTrue(r.ok, r.errors)

    def test_repeat_until(self):
        r = ok(prog(
            decls='var i: integer;\n',
            body='repeat\n  i := i + 1\nuntil i >= 10'
        ))
        self.assertTrue(r.ok, r.errors)

    def test_if_stmt(self):
        r = ok(prog(
            decls='var x, y: integer;\n',
            body='if x > 0 then y := 1 else y := 0'
        ))
        self.assertTrue(r.ok, r.errors)

    def test_forward_declaration(self):
        # BUG 2 fix: forward declaration followed by body must NOT be a duplicate.
        src = prog(
            decls='procedure p;\nforward;\nprocedure p;\nbegin\nend;\n'
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_builtin_writeln(self):
        r = ok(prog('writeln'))
        self.assertTrue(r.ok, r.errors)

    def test_standard_functions(self):
        r = ok(prog(
            decls='var x: integer;\n',
            body='x := abs(x)'
        ))
        self.assertTrue(r.ok, r.errors)

    def test_boolean_expression(self):
        r = ok(prog(
            decls='var a, b: boolean;\n',
            body='a := true;\nb := false'
        ))
        self.assertTrue(r.ok, r.errors)

    def test_nil_assignment(self):
        r = ok(prog(
            decls='type ptr = ^integer;\nvar p: ptr;\n',
            body='p := nil'
        ))
        self.assertTrue(r.ok, r.errors)

    def test_case_statement(self):
        r = ok(prog(
            decls='var x, y: integer;\n',
            body='case x of\n  1: y := 1;\n  2: y := 2\nend'
        ))
        self.assertTrue(r.ok, r.errors)

    def test_with_statement(self):
        # BUG 5 fix: WITH must open the record's field scope so that
        # bare field names are visible inside the body.
        src = prog(
            decls=(
                'type pt = record x: real; y: real end;\n'
                'var p: pt;\n'
            ),
            body='with p do x := 0.0'
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_recursive_function(self):
        src = """\
program Fact;
var n: integer;
function fact(x: integer): integer;
begin
  if x <= 1 then
    fact := 1
  else
    fact := x * fact(x - 1)
end;
begin
  n := fact(5)
end.
"""
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_complex_program(self):
        src = """\
program BubbleSort;
const maxn = 10;
type arr = array[1..10] of integer;
var a: arr;
    i, j, tmp: integer;
begin
  for i := 1 to maxn do
    for j := 1 to maxn - 1 do
      if a[j] > a[j + 1] then begin
        tmp := a[j];
        a[j] := a[j + 1];
        a[j + 1] := tmp
      end
end.
"""
        r = ok(src)
        self.assertTrue(r.ok, r.errors)


# ---------------------------------------------------------------------------
# 2. Undeclared identifier errors
# ---------------------------------------------------------------------------

class TestUndeclaredIdentifiers(unittest.TestCase):

    def test_undeclared_var_in_assign(self):
        r = err(prog('x := 1'))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)

    def test_undeclared_var_in_rhs(self):
        r = err(prog('y := x', decls='var y: integer;\n'))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)

    def test_undeclared_proc_call(self):
        r = err(prog('foo'))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)

    def test_undeclared_func_call(self):
        r = err(prog('x := bar(1)', decls='var x: integer;\n'))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)

    def test_undeclared_for_var(self):
        r = err(prog('for i := 1 to 10 do writeln'))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)

    def test_undeclared_in_condition(self):
        r = err(prog('if unknown > 0 then writeln'))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)

    def test_undeclared_type(self):
        r = err(prog(decls='var x: mytype;\n', body=''))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)

    def test_out_of_scope(self):
        src = prog(
            decls='procedure p;\nvar local: integer;\nbegin\nend;\n',
            body='local := 1'
        )
        r = err(src)
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)

    def test_writeln_args_undeclared(self):
        r = err(prog("writeln(undeclared_var)"))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)


# ---------------------------------------------------------------------------
# 3. Duplicate declaration errors
# ---------------------------------------------------------------------------

class TestDuplicateDeclarations(unittest.TestCase):

    def test_duplicate_var(self):
        r = err(prog(decls='var x: integer;\n    x: real;\n', body=''))
        self.assertTrue(has_error(r, 'duplicate_declaration'), r.errors)

    def test_duplicate_const(self):
        r = err(prog(decls='const a = 1;\n      a = 2;\n', body=''))
        self.assertTrue(has_error(r, 'duplicate_declaration'), r.errors)

    def test_duplicate_type(self):
        r = err(prog(decls='type t = integer;\n     t = real;\n', body=''))
        self.assertTrue(has_error(r, 'duplicate_declaration'), r.errors)

    def test_duplicate_procedure(self):
        src = prog(
            decls=(
                'procedure p;\nbegin\nend;\n'
                'procedure p;\nbegin\nend;\n'
            )
        )
        r = err(src)
        self.assertTrue(has_error(r, 'duplicate_declaration'), r.errors)

    def test_var_and_const_same_name(self):
        r = err(prog(decls='const x = 1;\nvar x: integer;\n', body=''))
        self.assertTrue(has_error(r, 'duplicate_declaration'), r.errors)


# ---------------------------------------------------------------------------
# 4. Type mismatch errors
# ---------------------------------------------------------------------------

class TestTypeMismatch(unittest.TestCase):

    def test_string_to_integer(self):
        r = err(prog("x := 'hello'", decls='var x: integer;\n'))
        self.assertTrue(has_error(r, 'type_mismatch'), r.errors)

    def test_real_to_integer(self):
        # Assigning real to integer is not allowed in strict Pascal
        r = err(prog('x := 3.14', decls='var x: integer;\n'))
        self.assertTrue(has_error(r, 'type_mismatch'), r.errors)

    def test_integer_to_real_ok(self):
        # Integer can widen to real — should NOT be an error
        r = err(prog('x := 1', decls='var x: real;\n'))
        self.assertFalse(has_error(r, 'type_mismatch'), r.errors)


# ---------------------------------------------------------------------------
# 5. SemanticError dataclass shape
# ---------------------------------------------------------------------------

class TestSemanticErrorShape(unittest.TestCase):

    def test_error_has_kind(self):
        r = err(prog('missing_var := 1'))
        e = r.errors[0]
        self.assertIsInstance(e.kind, str)
        self.assertGreater(len(e.kind), 0)

    def test_error_has_line(self):
        r = err(prog('missing_var := 1'))
        e = r.errors[0]
        self.assertIsInstance(e.line, int)

    def test_error_has_message(self):
        r = err(prog('missing_var := 1'))
        e = r.errors[0]
        self.assertIsInstance(e.message, str)
        self.assertGreater(len(e.message), 0)

    def test_error_str_format(self):
        r = err(prog('missing_var := 1'))
        s = str(r.errors[0])
        self.assertIn('[SemanticError]', s)
        self.assertIn('undeclared_identifier', s)

    def test_ok_when_no_errors(self):
        r = ok(prog())
        self.assertTrue(r.ok)

    def test_not_ok_when_errors(self):
        r = err(prog('missing_var := 1'))
        self.assertFalse(r.ok)

    def test_bool_true_when_ok(self):
        r = ok(prog())
        self.assertTrue(bool(r))

    def test_bool_false_when_errors(self):
        r = err(prog('missing_var := 1'))
        self.assertFalse(bool(r))


# ---------------------------------------------------------------------------
# 6. Scope tests
# ---------------------------------------------------------------------------

class TestScoping(unittest.TestCase):

    def test_inner_shadows_outer(self):
        src = prog(
            decls=(
                'var x: integer;\n'
                'procedure p;\n'
                'var x: real;\n'  # shadows outer x — OK in Pascal
                'begin\n  x := 1.0\nend;\n'
            ),
            body='x := 1'
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_global_visible_in_proc(self):
        r = ok(prog(
            decls=(
                'var g: integer;\n'
                'procedure p;\nbegin\n  g := 42\nend;\n'
            ),
            body='p'
        ))
        self.assertTrue(r.ok, r.errors)

    def test_local_not_visible_outside(self):
        src = prog(
            decls='procedure p;\nvar local: integer;\nbegin\nend;\n',
            body='local := 1'
        )
        r = err(src)
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)

    def test_param_visible_in_body(self):
        r = ok(prog(
            decls='procedure add(a, b: integer);\nbegin\n  writeln(a)\nend;\n',
            body='add(1, 2)'
        ))
        self.assertTrue(r.ok, r.errors)

    def test_function_result_assignable(self):
        src = prog(
            decls='function square(x: integer): integer;\nbegin\n  square := x * x\nend;\n',
            body='writeln'
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)


# ---------------------------------------------------------------------------
# 7. Arity checking (BUG 3)
# ---------------------------------------------------------------------------

class TestArityChecking(unittest.TestCase):

    def _func_src(self, call: str) -> str:
        return prog(
            decls=(
                'var n: integer;\n'
                'function double(x: integer): integer;\n'
                'begin\n  double := x * 2\nend;\n'
            ),
            body=call,
        )

    def _proc_src(self, call: str) -> str:
        return prog(
            decls='procedure greet(name: string; times: integer);\nbegin\nend;\n',
            body=call,
        )

    def test_function_correct_arity(self):
        r = ok(self._func_src('n := double(5)'))
        self.assertTrue(r.ok, r.errors)

    def test_function_arity_too_many(self):
        r = err(self._func_src('n := double(1, 2, 3)'))
        self.assertTrue(has_error(r, 'arity_mismatch'), r.errors)

    def test_function_arity_too_few(self):
        r = err(self._func_src('n := double()'))
        self.assertTrue(has_error(r, 'arity_mismatch'), r.errors)

    def test_procedure_correct_arity(self):
        r = ok(self._proc_src("greet('Alice', 3)"))
        self.assertTrue(r.ok, r.errors)

    def test_procedure_arity_mismatch(self):
        r = err(self._proc_src("greet('Alice')"))
        self.assertTrue(has_error(r, 'arity_mismatch'), r.errors)

    def test_builtin_arity_not_checked(self):
        # Built-in functions must NOT trigger arity_mismatch regardless of
        # how many arguments are passed (they are variadic/overloaded).
        r = ok(prog(
            decls='var x: integer;\n',
            body='x := abs(x)',
        ))
        self.assertFalse(has_error(r, 'arity_mismatch'), r.errors)

    def test_zero_param_function_called_with_args(self):
        src = prog(
            decls=(
                'var n: integer;\n'
                'function answer: integer;\n'
                'begin\n  answer := 42\nend;\n'
            ),
            body='n := answer(99)',
        )
        r = err(src)
        self.assertTrue(has_error(r, 'arity_mismatch'), r.errors)


# ---------------------------------------------------------------------------
# 8. Type compatibility additions (BUG 4)
# ---------------------------------------------------------------------------

class TestTypeCompatibilityExtended(unittest.TestCase):

    def test_char_assign_single_string_ok(self):
        # BUG 4 fix: char := 'A' must NOT be a type_mismatch.
        r = ok(prog(
            decls='var ch: char;\n',
            body="ch := 'A'",
        ))
        self.assertTrue(r.ok, r.errors)

    def test_char_assign_multi_string(self):
        # Assigning a multi-char string to char is also allowed at the semantic
        # level (length is a runtime concern), so no error expected here either.
        r = ok(prog(
            decls='var ch: char;\n',
            body="ch := 'AB'",
        ))
        self.assertIsInstance(r, SemanticResult)

    def test_integer_assign_string_still_errors(self):
        # Assigning a string to an integer variable must still be a type_mismatch.
        r = err(prog("x := 'hello'", decls='var x: integer;\n'))
        self.assertTrue(has_error(r, 'type_mismatch'), r.errors)


# ---------------------------------------------------------------------------
# 9. WITH scope (BUG 5)
# ---------------------------------------------------------------------------

class TestWithScope(unittest.TestCase):

    def test_with_fields_visible_in_body(self):
        src = prog(
            decls=(
                'type pt = record x: real; y: real end;\n'
                'var p: pt;\n'
            ),
            body='with p do begin\n  x := 1.0;\n  y := 2.0\nend',
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_with_field_undeclared_outside_body(self):
        # 'x' must not leak outside the WITH scope.
        src = prog(
            decls=(
                'type pt = record x: real end;\n'
                'var p: pt;\n'
                '    q: real;\n'
            ),
            body='with p do q := x;\nq := x',
        )
        r = err(src)
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)

    def test_with_multiple_records(self):
        src = prog(
            decls=(
                'type vec = record vx: real; vy: real end;\n'
                'var a, b: vec;\n'
                '    s: real;\n'
            ),
            body='with a, b do begin\n  vx := 0.0;\n  vy := 0.0\nend',
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)


# ---------------------------------------------------------------------------
# 10. Forward declarations (BUG 2)
# ---------------------------------------------------------------------------

class TestForwardDeclarations(unittest.TestCase):

    def test_forward_proc_no_duplicate(self):
        src = prog(
            decls=(
                'procedure p;\nforward;\n'
                'procedure p;\nbegin\nend;\n'
            ),
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_forward_func_no_duplicate(self):
        src = prog(
            decls=(
                'function f(x: integer): integer;\nforward;\n'
                'function f(x: integer): integer;\nbegin\n  f := x\nend;\n'
            ),
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_two_bodies_without_forward_is_duplicate(self):
        src = prog(
            decls=(
                'procedure p;\nbegin\nend;\n'
                'procedure p;\nbegin\nend;\n'
            ),
        )
        r = err(src)
        self.assertTrue(has_error(r, 'duplicate_declaration'), r.errors)


# ---------------------------------------------------------------------------
# 11. BoolLit / true-false as literals (PROBLEMA 12)
# ---------------------------------------------------------------------------

class TestBoolLit(unittest.TestCase):

    def test_true_assignable_to_boolean(self):
        r = ok(prog(
            decls='var flag: boolean;\n',
            body='flag := true',
        ))
        self.assertTrue(r.ok, r.errors)

    def test_false_assignable_to_boolean(self):
        r = ok(prog(
            decls='var flag: boolean;\n',
            body='flag := false',
        ))
        self.assertTrue(r.ok, r.errors)

    def test_bool_assigned_to_integer_errors(self):
        r = err(prog(
            decls='var x: integer;\n',
            body='x := true',
        ))
        self.assertTrue(has_error(r, 'type_mismatch'), r.errors)


# ---------------------------------------------------------------------------
# 12. main keyword removed (BUG 1)
# ---------------------------------------------------------------------------

class TestMainNotReserved(unittest.TestCase):

    def test_main_as_variable(self):
        from mini_pascal_parser import parse
        r = parse("program Test;\nvar main: integer;\nbegin\nmain := 1\nend.\n")
        self.assertFalse(r.parse_errors, r.parse_errors)
        self.assertFalse(r.lex_errors, r.lex_errors)

    def test_main_as_procedure_name(self):
        from mini_pascal_parser import parse
        r = parse(
            "program Test;\nprocedure main;\nbegin\nend;\nbegin\nmain\nend.\n"
        )
        self.assertFalse(r.parse_errors, r.parse_errors)


# ---------------------------------------------------------------------------
# 13. Undeclared record field
# ---------------------------------------------------------------------------

class TestUndeclaredField(unittest.TestCase):

    def test_undeclared_field_error(self):
        src = prog(
            decls=(
                'type point = record x: real; y: real end;\n'
                'var p: point;\n'
            ),
            body='p.z := 1.0',
        )
        r = err(src)
        self.assertTrue(has_error(r, 'undeclared_field'), r.errors)

    def test_declared_field_ok(self):
        src = prog(
            decls=(
                'type point = record x: real; y: real end;\n'
                'var p: point;\n'
            ),
            body='p.x := 1.0',
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_field_on_undeclared_var_no_spurious_field_error(self):
        # T_ANY from undeclared base must not also emit undeclared_field.
        r = err(prog(body='unknown_var.field := 1'))
        self.assertFalse(has_error(r, 'undeclared_field'), r.errors)
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)


# ---------------------------------------------------------------------------
# 14. GOTO — undeclared label check
# ---------------------------------------------------------------------------

class TestGotoStmt(unittest.TestCase):

    def test_goto_declared_label_ok(self):
        src = (
            "program Test;\n"
            "label 10;\n"
            "begin\n"
            "  goto 10;\n"
            "  10: writeln\n"
            "end.\n"
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_goto_undeclared_label_error(self):
        src = (
            "program Test;\n"
            "begin\n"
            "  goto 99\n"
            "end.\n"
        )
        r = err(src)
        self.assertTrue(has_error(r, 'undeclared_label'), r.errors)

    def test_goto_string_label_ok(self):
        src = (
            "program Test;\n"
            "label exit_loop;\n"
            "begin\n"
            "  goto exit_loop;\n"
            "  exit_loop: writeln\n"
            "end.\n"
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_goto_string_label_undeclared_error(self):
        src = (
            "program Test;\n"
            "begin\n"
            "  goto nowhere\n"
            "end.\n"
        )
        r = err(src)
        self.assertTrue(has_error(r, 'undeclared_label'), r.errors)


# ---------------------------------------------------------------------------
# 15. Boolean condition checks — if / while / repeat
# ---------------------------------------------------------------------------

class TestBooleanConditions(unittest.TestCase):

    def test_if_comparison_ok(self):
        r = ok(prog(decls='var i: integer;\n', body='if i > 0 then writeln'))
        self.assertTrue(r.ok, r.errors)

    def test_if_bool_var_ok(self):
        r = ok(prog(decls='var flag: boolean;\n', body='if flag then writeln'))
        self.assertTrue(r.ok, r.errors)

    def test_if_integer_condition_error(self):
        r = err(prog(decls='var i: integer;\n', body='if i then writeln'))
        self.assertTrue(has_error(r, 'type_mismatch'), r.errors)

    def test_if_real_condition_error(self):
        r = err(prog(decls='var x: real;\n', body='if x then writeln'))
        self.assertTrue(has_error(r, 'type_mismatch'), r.errors)

    def test_if_undeclared_no_extra_error(self):
        r = err(prog(body='if ghost then writeln'))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)
        self.assertFalse(has_error(r, 'type_mismatch'), r.errors)

    def test_while_comparison_ok(self):
        r = ok(prog(decls='var i: integer;\n', body='while i < 10 do i := i + 1'))
        self.assertTrue(r.ok, r.errors)

    def test_while_bool_var_ok(self):
        r = ok(prog(decls='var flag: boolean;\n', body='while flag do writeln'))
        self.assertTrue(r.ok, r.errors)

    def test_while_integer_condition_error(self):
        r = err(prog(decls='var i: integer;\n', body='while i do writeln'))
        self.assertTrue(has_error(r, 'type_mismatch'), r.errors)

    def test_while_undeclared_no_extra_error(self):
        r = err(prog(body='while ghost do writeln'))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)
        self.assertFalse(has_error(r, 'type_mismatch'), r.errors)

    def test_repeat_comparison_ok(self):
        r = ok(prog(decls='var i: integer;\n',
                    body='repeat\n  i := i + 1\nuntil i >= 10'))
        self.assertTrue(r.ok, r.errors)

    def test_repeat_bool_var_ok(self):
        r = ok(prog(decls='var done: boolean;\n',
                    body='repeat\n  writeln\nuntil done'))
        self.assertTrue(r.ok, r.errors)

    def test_repeat_integer_condition_error(self):
        r = err(prog(decls='var i: integer;\n',
                     body='repeat\n  i := i + 1\nuntil i'))
        self.assertTrue(has_error(r, 'type_mismatch'), r.errors)

    def test_repeat_undeclared_no_extra_error(self):
        r = err(prog(body='repeat\n  writeln\nuntil ghost'))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)
        self.assertFalse(has_error(r, 'type_mismatch'), r.errors)


# ---------------------------------------------------------------------------
# 16. Pointer dereference — non-pointer base
# ---------------------------------------------------------------------------

class TestDerefVar(unittest.TestCase):

    def test_deref_pointer_ok(self):
        src = prog(
            decls='var p: ^integer;\n    x: integer;\n',
            body='x := p^',
        )
        r = ok(src)
        self.assertTrue(r.ok, r.errors)

    def test_deref_non_pointer_error(self):
        src = prog(decls='var i: integer;\n', body='writeln(i^)')
        r = err(src)
        self.assertTrue(has_error(r, 'type_mismatch'), r.errors)

    def test_deref_undeclared_no_extra_error(self):
        r = err(prog(body='writeln(ghost^)'))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)
        self.assertFalse(has_error(r, 'type_mismatch'), r.errors)


# ---------------------------------------------------------------------------
# 17. AND / OR — operands must be boolean
# ---------------------------------------------------------------------------

class TestBooleanOperators(unittest.TestCase):

    def test_and_bool_operands_ok(self):
        r = ok(prog(decls='var a, b: boolean;\n', body='if a and b then writeln'))
        self.assertTrue(r.ok, r.errors)

    def test_or_bool_operands_ok(self):
        r = ok(prog(decls='var a, b: boolean;\n', body='if a or b then writeln'))
        self.assertTrue(r.ok, r.errors)

    def test_and_integer_left_error(self):
        r = err(prog(decls='var i: integer;\n    b: boolean;\n',
                     body='if i and b then writeln'))
        self.assertTrue(has_error(r, 'type_mismatch'), r.errors)

    def test_and_integer_right_error(self):
        r = err(prog(decls='var b: boolean;\n    i: integer;\n',
                     body='if b and i then writeln'))
        self.assertTrue(has_error(r, 'type_mismatch'), r.errors)

    def test_or_integer_operands_error(self):
        r = err(prog(decls='var i, j: integer;\n',
                     body='if i or j then writeln'))
        self.assertTrue(has_error(r, 'type_mismatch'), r.errors)

    def test_and_undeclared_no_extra_error(self):
        r = err(prog(decls='var b: boolean;\n', body='if b and ghost then writeln'))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)
        self.assertFalse(has_error(r, 'type_mismatch'), r.errors)


# ---------------------------------------------------------------------------
# 18. NOT — operand must be boolean
# ---------------------------------------------------------------------------

class TestNotOperator(unittest.TestCase):

    def test_not_bool_ok(self):
        r = ok(prog(decls='var flag: boolean;\n', body='if not flag then writeln'))
        self.assertTrue(r.ok, r.errors)

    def test_not_integer_error(self):
        r = err(prog(decls='var i: integer;\n', body='if not i then writeln'))
        self.assertTrue(has_error(r, 'type_mismatch'), r.errors)

    def test_not_undeclared_no_extra_error(self):
        r = err(prog(body='if not ghost then writeln'))
        self.assertTrue(has_error(r, 'undeclared_identifier'), r.errors)
        self.assertFalse(has_error(r, 'type_mismatch'), r.errors)


if __name__ == '__main__':
    unittest.main()
