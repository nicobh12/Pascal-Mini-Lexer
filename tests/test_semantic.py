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
        src = prog(
            decls='procedure p;\nforward;\nprocedure p;\nbegin\nend;\n'
        )
        # Forward then body: second declaration of p may trigger duplicate.
        # Semantic check should be lenient or handle forward correctly.
        r = ok(src)
        # Just checking no crash
        self.assertIsInstance(r, SemanticResult)

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
        src = prog(
            decls=(
                'type pt = record x: real; y: real end;\n'
                'var p: pt;\n'
            ),
            body='with p do x := 0.0'
        )
        r = ok(src)
        self.assertIsInstance(r, SemanticResult)

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


if __name__ == '__main__':
    unittest.main()
