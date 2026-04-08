"""
test_parser.py
Comprehensive test suite for the Mini-Pascal recursive-descent parser.
"""
import unittest
from mini_pascal_parser import (
    parse,
    Program, Block,
    ConstDef, TypeDef, VarDecl, ProcDecl, FuncDecl, Param,
    SimpleType, SubrangeType, ArrayType, RecordType, SetType, FileType, PointerType,
    CompoundStmt, AssignStmt, IfStmt, WhileStmt, ForStmt, RepeatStmt,
    CaseStmt, GotoStmt, WritelnStmt, ProcCallStmt, WithStmt,
    IntLit, RealLit, StrLit, NilLit, BinOp, UnaryOp, FuncCall,
    Var, IndexVar, FieldVar, DerefVar,
    ParseError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def prog(body: str = '', decls: str = '') -> str:
    """Wrap body and declarations in a minimal valid program."""
    return f"program Test;\n{decls}begin\n{body}\nend.\n"


def parse_ok(source: str) -> Program:
    """Parse source, assert no errors, return the Program node."""
    result = parse(source)
    assert not result.parse_errors, \
        f"Unexpected parse errors: {result.parse_errors}"
    assert not result.lex_errors, \
        f"Unexpected lex errors: {result.lex_errors}"
    return result.program


def parse_err(source: str):
    """Parse source and return the ParseResult (errors expected)."""
    return parse(source)


# ---------------------------------------------------------------------------
# 1. Program Structure
# ---------------------------------------------------------------------------

class TestProgramStructure(unittest.TestCase):

    def test_minimal_program(self):
        p = parse_ok(prog())
        self.assertIsInstance(p, Program)
        self.assertEqual(p.name, 'Test')
        self.assertEqual(p.params, [])

    def test_program_name_case_insensitive(self):
        p = parse_ok("program HELLO;\nbegin\nend.\n")
        self.assertEqual(p.name, 'HELLO')

    def test_program_with_params(self):
        p = parse_ok("program Foo(input, output);\nbegin\nend.\n")
        self.assertEqual(p.params, ['input', 'output'])

    def test_block_is_set(self):
        p = parse_ok(prog())
        self.assertIsInstance(p.block, Block)

    def test_empty_compound_body(self):
        p = parse_ok(prog())
        body = p.block.body
        self.assertIsInstance(body, CompoundStmt)
        self.assertEqual(body.stmts, [])


# ---------------------------------------------------------------------------
# 2. Label Declaration
# ---------------------------------------------------------------------------

class TestLabelDeclaration(unittest.TestCase):

    def test_single_integer_label(self):
        p = parse_ok(prog(decls='label 10;\n'))
        self.assertEqual(p.block.labels, [10])

    def test_multiple_labels(self):
        p = parse_ok(prog(decls='label 1, 2, 3;\n'))
        self.assertEqual(p.block.labels, [1, 2, 3])

    def test_id_label(self):
        p = parse_ok(prog(decls='label exit_loop;\n'))
        self.assertEqual(p.block.labels, ['exit_loop'])


# ---------------------------------------------------------------------------
# 3. Const Declarations
# ---------------------------------------------------------------------------

class TestConstDeclarations(unittest.TestCase):

    def test_integer_const(self):
        p = parse_ok(prog(decls='const maxn = 100;\n'))
        c = p.block.consts[0]
        self.assertIsInstance(c, ConstDef)
        self.assertEqual(c.name, 'maxn')
        self.assertIsInstance(c.value, IntLit)
        self.assertEqual(c.value.value, 100)

    def test_real_const(self):
        p = parse_ok(prog(decls='const pi = 3.14159;\n'))
        c = p.block.consts[0]
        self.assertIsInstance(c.value, RealLit)
        self.assertAlmostEqual(c.value.value, 3.14159)

    def test_string_const(self):
        p = parse_ok(prog(decls="const greeting = 'Hello';\n"))
        c = p.block.consts[0]
        self.assertIsInstance(c.value, StrLit)
        self.assertEqual(c.value.value, 'Hello')

    def test_negative_const(self):
        p = parse_ok(prog(decls='const minval = -1;\n'))
        c = p.block.consts[0]
        self.assertIsInstance(c.value, UnaryOp)
        self.assertEqual(c.value.op, 'MINUS')
        self.assertIsInstance(c.value.operand, IntLit)

    def test_named_const(self):
        p = parse_ok(prog(decls='const limit = maxn;\n'))
        c = p.block.consts[0]
        self.assertIsInstance(c.value, Var)
        self.assertEqual(c.value.name, 'maxn')

    def test_multiple_consts(self):
        src = prog(decls='const a = 1;\n      b = 2;\n      c = 3;\n')
        p = parse_ok(src)
        self.assertEqual(len(p.block.consts), 3)
        names = [c.name for c in p.block.consts]
        self.assertEqual(names, ['a', 'b', 'c'])


# ---------------------------------------------------------------------------
# 4. Type Declarations
# ---------------------------------------------------------------------------

class TestTypeDeclarations(unittest.TestCase):

    def test_type_alias(self):
        p = parse_ok(prog(decls='type myint = integer;\n'))
        t = p.block.types[0]
        self.assertIsInstance(t, TypeDef)
        self.assertEqual(t.name, 'myint')
        self.assertIsInstance(t.type_node, SimpleType)
        self.assertEqual(t.type_node.name, 'integer')

    def test_integer_subrange(self):
        p = parse_ok(prog(decls='type digit = 0..9;\n'))
        t = p.block.types[0]
        self.assertIsInstance(t.type_node, SubrangeType)
        self.assertIsInstance(t.type_node.low, IntLit)
        self.assertEqual(t.type_node.low.value, 0)
        self.assertIsInstance(t.type_node.high, IntLit)
        self.assertEqual(t.type_node.high.value, 9)

    def test_negative_subrange(self):
        p = parse_ok(prog(decls='type signed = -128..127;\n'))
        t = p.block.types[0]
        self.assertIsInstance(t.type_node, SubrangeType)
        self.assertIsInstance(t.type_node.low, UnaryOp)

    def test_array_type(self):
        p = parse_ok(prog(decls='type arr = array[1..10] of integer;\n'))
        t = p.block.types[0]
        self.assertIsInstance(t.type_node, ArrayType)
        self.assertFalse(t.type_node.packed)
        self.assertEqual(len(t.type_node.indices), 1)
        self.assertIsInstance(t.type_node.element_type, SimpleType)

    def test_packed_array_type(self):
        p = parse_ok(prog(decls='type str = packed array[1..80] of char;\n'))
        t = p.block.types[0]
        self.assertIsInstance(t.type_node, ArrayType)
        self.assertTrue(t.type_node.packed)

    def test_multidim_array(self):
        p = parse_ok(prog(decls='type matrix = array[1..3, 1..3] of real;\n'))
        t = p.block.types[0]
        self.assertIsInstance(t.type_node, ArrayType)
        self.assertEqual(len(t.type_node.indices), 2)

    def test_record_type(self):
        src = prog(decls='type point = record x: real; y: real end;\n')
        p = parse_ok(src)
        t = p.block.types[0]
        self.assertIsInstance(t.type_node, RecordType)
        self.assertEqual(len(t.type_node.fields), 2)

    def test_record_multifield(self):
        src = prog(decls='type person = record name: str; age: integer end;\n')
        p = parse_ok(src)
        t = p.block.types[0]
        # Both fields in list
        self.assertEqual(len(t.type_node.fields), 2)
        names0, _ = t.type_node.fields[0]
        self.assertEqual(names0, ['name'])

    def test_record_trailing_semicolon(self):
        src = prog(decls='type pt = record x: real; y: real; end;\n')
        p = parse_ok(src)
        t = p.block.types[0]
        self.assertEqual(len(t.type_node.fields), 2)

    def test_pointer_type(self):
        p = parse_ok(prog(decls='type ptr = ^integer;\n'))
        t = p.block.types[0]
        self.assertIsInstance(t.type_node, PointerType)
        self.assertEqual(t.type_node.target, 'integer')

    def test_set_type(self):
        p = parse_ok(prog(decls='type charset = set of char;\n'))
        t = p.block.types[0]
        self.assertIsInstance(t.type_node, SetType)
        self.assertFalse(t.type_node.packed)

    def test_file_type(self):
        p = parse_ok(prog(decls='type intfile = file of integer;\n'))
        t = p.block.types[0]
        self.assertIsInstance(t.type_node, FileType)

    def test_multiple_type_defs(self):
        src = prog(decls='type a = integer;\n      b = real;\n')
        p = parse_ok(src)
        self.assertEqual(len(p.block.types), 2)


# ---------------------------------------------------------------------------
# 5. Var Declarations
# ---------------------------------------------------------------------------

class TestVarDeclarations(unittest.TestCase):

    def test_single_var(self):
        p = parse_ok(prog(decls='var x: integer;\n'))
        v = p.block.vars[0]
        self.assertIsInstance(v, VarDecl)
        self.assertEqual(v.names, ['x'])
        self.assertIsInstance(v.type_node, SimpleType)

    def test_multi_name_var(self):
        p = parse_ok(prog(decls='var x, y, z: real;\n'))
        v = p.block.vars[0]
        self.assertEqual(v.names, ['x', 'y', 'z'])

    def test_multiple_var_decls(self):
        src = prog(decls='var a: integer;\n    b: real;\n    c: boolean;\n')
        p = parse_ok(src)
        self.assertEqual(len(p.block.vars), 3)

    def test_var_array_type(self):
        p = parse_ok(prog(decls='var arr: array[0..9] of integer;\n'))
        v = p.block.vars[0]
        self.assertIsInstance(v.type_node, ArrayType)

    def test_var_record_type(self):
        src = prog(decls='var pt: record x: real; y: real end;\n')
        p = parse_ok(src)
        v = p.block.vars[0]
        self.assertIsInstance(v.type_node, RecordType)


# ---------------------------------------------------------------------------
# 6. Subprogram Declarations
# ---------------------------------------------------------------------------

class TestSubprogramDeclarations(unittest.TestCase):

    def test_procedure_no_params(self):
        src = prog(decls='procedure greet;\nbegin\nend;\n')
        p = parse_ok(src)
        proc = p.block.subprograms[0]
        self.assertIsInstance(proc, ProcDecl)
        self.assertEqual(proc.name, 'greet')
        self.assertEqual(proc.params, [])
        self.assertFalse(proc.forward)

    def test_procedure_with_params(self):
        src = prog(decls='procedure add(a, b: integer);\nbegin\nend;\n')
        p = parse_ok(src)
        proc = p.block.subprograms[0]
        self.assertEqual(len(proc.params), 1)
        param = proc.params[0]
        self.assertIsInstance(param, Param)
        self.assertEqual(param.names, ['a', 'b'])
        self.assertEqual(param.type_name, 'integer')
        self.assertFalse(param.by_ref)

    def test_procedure_var_param(self):
        src = prog(decls='procedure inc(var x: integer);\nbegin\nend;\n')
        p = parse_ok(src)
        param = p.block.subprograms[0].params[0]
        self.assertTrue(param.by_ref)

    def test_procedure_multiple_param_sections(self):
        src = prog(decls='procedure foo(x: integer; var y: real);\nbegin\nend;\n')
        p = parse_ok(src)
        proc = p.block.subprograms[0]
        self.assertEqual(len(proc.params), 2)

    def test_function_declaration(self):
        src = prog(decls='function square(x: integer): integer;\nbegin\nend;\n')
        p = parse_ok(src)
        fn = p.block.subprograms[0]
        self.assertIsInstance(fn, FuncDecl)
        self.assertEqual(fn.name, 'square')
        self.assertEqual(fn.return_type, 'integer')
        self.assertFalse(fn.forward)

    def test_forward_procedure(self):
        src = prog(decls='procedure foo;\nforward;\n')
        p = parse_ok(src)
        proc = p.block.subprograms[0]
        self.assertTrue(proc.forward)
        self.assertIsNone(proc.body)

    def test_forward_function(self):
        src = prog(decls='function bar: integer;\nforward;\n')
        p = parse_ok(src)
        fn = p.block.subprograms[0]
        self.assertTrue(fn.forward)

    def test_multiple_subprograms(self):
        src = prog(decls=(
            'procedure a;\nbegin\nend;\n'
            'function b: integer;\nbegin\nend;\n'
        ))
        p = parse_ok(src)
        self.assertEqual(len(p.block.subprograms), 2)


# ---------------------------------------------------------------------------
# 7. Compound Statement
# ---------------------------------------------------------------------------

class TestCompoundStatement(unittest.TestCase):

    def test_empty_compound(self):
        p = parse_ok(prog())
        self.assertEqual(p.block.body.stmts, [])

    def test_single_stmt(self):
        p = parse_ok(prog('x := 1'))
        self.assertEqual(len(p.block.body.stmts), 1)

    def test_multiple_stmts(self):
        p = parse_ok(prog('x := 1;\ny := 2;\nz := 3'))
        self.assertEqual(len(p.block.body.stmts), 3)

    def test_trailing_semicolon(self):
        p = parse_ok(prog('x := 1;\ny := 2;\n'))
        self.assertEqual(len(p.block.body.stmts), 2)

    def test_nested_compound(self):
        p = parse_ok(prog('begin\n  x := 1;\n  y := 2\nend'))
        stmt = p.block.body.stmts[0]
        self.assertIsInstance(stmt, CompoundStmt)
        self.assertEqual(len(stmt.stmts), 2)


# ---------------------------------------------------------------------------
# 8. Assignment Statement
# ---------------------------------------------------------------------------

class TestAssignmentStatement(unittest.TestCase):

    def test_simple_assign(self):
        p = parse_ok(prog('x := 42'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s, AssignStmt)
        self.assertIsInstance(s.target, Var)
        self.assertEqual(s.target.name, 'x')
        self.assertIsInstance(s.value, IntLit)
        self.assertEqual(s.value.value, 42)

    def test_assign_expression(self):
        p = parse_ok(prog('x := a + b * 2'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.value, BinOp)
        self.assertEqual(s.value.op, 'PLUS')

    def test_array_element_assign(self):
        p = parse_ok(prog('arr[i] := 0'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.target, IndexVar)
        self.assertIsInstance(s.target.base, Var)
        self.assertEqual(s.target.base.name, 'arr')

    def test_multidim_array_assign(self):
        p = parse_ok(prog('m[i, j] := 1'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.target, IndexVar)
        self.assertEqual(len(s.target.indices), 2)

    def test_field_assign(self):
        p = parse_ok(prog('pt.x := 3.14'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.target, FieldVar)
        self.assertEqual(s.target.field_name, 'x')

    def test_deref_assign(self):
        p = parse_ok(prog('p^ := 99'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.target, DerefVar)

    def test_chained_field_assign(self):
        p = parse_ok(prog('a.b.c := 1'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.target, FieldVar)
        self.assertEqual(s.target.field_name, 'c')
        self.assertIsInstance(s.target.base, FieldVar)

    def test_string_assign(self):
        p = parse_ok(prog("msg := 'hello'"))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.value, StrLit)
        self.assertEqual(s.value.value, 'hello')


# ---------------------------------------------------------------------------
# 9. If Statement
# ---------------------------------------------------------------------------

class TestIfStatement(unittest.TestCase):

    def test_if_then(self):
        p = parse_ok(prog('if x > 0 then y := 1'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s, IfStmt)
        self.assertIsInstance(s.condition, BinOp)
        self.assertEqual(s.condition.op, 'GT')
        self.assertIsInstance(s.then_branch, AssignStmt)
        self.assertIsNone(s.else_branch)

    def test_if_then_else(self):
        p = parse_ok(prog('if x > 0 then y := 1 else y := 0'))
        s = p.block.body.stmts[0]
        self.assertIsNotNone(s.else_branch)
        self.assertIsInstance(s.else_branch, AssignStmt)

    def test_nested_if(self):
        src = prog('if a then if b then c := 1 else c := 2')
        p = parse_ok(src)
        outer = p.block.body.stmts[0]
        self.assertIsInstance(outer.then_branch, IfStmt)

    def test_if_with_compound(self):
        src = prog('if x then begin\n  y := 1;\n  z := 2\nend')
        p = parse_ok(src)
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.then_branch, CompoundStmt)

    def test_if_boolean_condition(self):
        p = parse_ok(prog('if a and b then x := 1'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.condition, BinOp)
        self.assertEqual(s.condition.op, 'AND')


# ---------------------------------------------------------------------------
# 10. While Statement
# ---------------------------------------------------------------------------

class TestWhileStatement(unittest.TestCase):

    def test_while_basic(self):
        p = parse_ok(prog('while i < 10 do i := i + 1'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s, WhileStmt)
        self.assertIsInstance(s.condition, BinOp)
        self.assertEqual(s.condition.op, 'LT')

    def test_while_with_compound(self):
        src = prog('while x > 0 do begin\n  x := x - 1\nend')
        p = parse_ok(src)
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.body, CompoundStmt)

    def test_while_not_condition(self):
        p = parse_ok(prog('while not done do i := i + 1'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.condition, UnaryOp)
        self.assertEqual(s.condition.op, 'NOT')


# ---------------------------------------------------------------------------
# 11. For Statement
# ---------------------------------------------------------------------------

class TestForStatement(unittest.TestCase):

    def test_for_to(self):
        p = parse_ok(prog('for i := 1 to 10 do writeln'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s, ForStmt)
        self.assertEqual(s.var, 'i')
        self.assertEqual(s.direction, 'to')
        self.assertIsInstance(s.start, IntLit)
        self.assertIsInstance(s.end, IntLit)

    def test_for_downto(self):
        p = parse_ok(prog('for i := 10 downto 1 do x := x + i'))
        s = p.block.body.stmts[0]
        self.assertEqual(s.direction, 'downto')

    def test_for_expr_bounds(self):
        p = parse_ok(prog('for k := lo to hi do process(k)'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.start, Var)
        self.assertIsInstance(s.end, Var)

    def test_for_with_compound(self):
        src = prog('for i := 1 to n do begin\n  sum := sum + i\nend')
        p = parse_ok(src)
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.body, CompoundStmt)


# ---------------------------------------------------------------------------
# 12. Repeat Statement
# ---------------------------------------------------------------------------

class TestRepeatStatement(unittest.TestCase):

    def test_repeat_basic(self):
        p = parse_ok(prog('repeat\n  i := i + 1\nuntil i >= 10'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s, RepeatStmt)
        self.assertEqual(len(s.body), 1)
        self.assertIsInstance(s.condition, BinOp)
        self.assertEqual(s.condition.op, 'GEQ')

    def test_repeat_multiple_stmts(self):
        src = prog('repeat\n  x := x + 1;\n  y := y - 1\nuntil x = y')
        p = parse_ok(src)
        s = p.block.body.stmts[0]
        self.assertEqual(len(s.body), 2)


# ---------------------------------------------------------------------------
# 13. Case Statement
# ---------------------------------------------------------------------------

class TestCaseStatement(unittest.TestCase):

    def test_case_single_element(self):
        src = prog('case x of\n  1: y := 1\nend')
        p = parse_ok(src)
        s = p.block.body.stmts[0]
        self.assertIsInstance(s, CaseStmt)
        self.assertEqual(len(s.elements), 1)
        labels, stmt = s.elements[0]
        self.assertEqual(len(labels), 1)
        self.assertIsInstance(labels[0], IntLit)

    def test_case_multiple_elements(self):
        src = prog(
            'case op of\n'
            '  1: x := x + 1;\n'
            '  2: x := x - 1;\n'
            '  3: x := x * 2\n'
            'end'
        )
        p = parse_ok(src)
        s = p.block.body.stmts[0]
        self.assertEqual(len(s.elements), 3)

    def test_case_multiple_labels(self):
        src = prog('case c of\n  1, 2, 3: x := 0\nend')
        p = parse_ok(src)
        s = p.block.body.stmts[0]
        labels, _ = s.elements[0]
        self.assertEqual(len(labels), 3)

    def test_case_trailing_semicolon(self):
        src = prog('case x of\n  1: y := 1;\n  2: y := 2;\nend')
        p = parse_ok(src)
        s = p.block.body.stmts[0]
        self.assertEqual(len(s.elements), 2)

    def test_case_expression(self):
        src = prog('case grade of\n  10: writeln\nend')
        p = parse_ok(src)
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.expression, Var)
        self.assertEqual(s.expression.name, 'grade')


# ---------------------------------------------------------------------------
# 14. Goto Statement
# ---------------------------------------------------------------------------

class TestGotoStatement(unittest.TestCase):

    def test_goto_integer(self):
        p = parse_ok(prog('goto 99'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s, GotoStmt)
        self.assertEqual(s.label, 99)

    def test_goto_id(self):
        p = parse_ok(prog('goto exit_loop'))
        s = p.block.body.stmts[0]
        self.assertEqual(s.label, 'exit_loop')


# ---------------------------------------------------------------------------
# 15. Writeln Statement
# ---------------------------------------------------------------------------

class TestWritelnStatement(unittest.TestCase):

    def test_writeln_no_args(self):
        p = parse_ok(prog('writeln'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s, WritelnStmt)
        self.assertEqual(s.args, [])

    def test_writeln_one_arg(self):
        p = parse_ok(prog("writeln('hello')"))
        s = p.block.body.stmts[0]
        self.assertEqual(len(s.args), 1)
        self.assertIsInstance(s.args[0], StrLit)

    def test_writeln_multiple_args(self):
        p = parse_ok(prog("writeln('x =', x, ' y =', y)"))
        s = p.block.body.stmts[0]
        self.assertEqual(len(s.args), 4)

    def test_writeln_expression_arg(self):
        p = parse_ok(prog('writeln(a + b)'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.args[0], BinOp)


# ---------------------------------------------------------------------------
# 16. Procedure Call Statement
# ---------------------------------------------------------------------------

class TestProcedureCallStatement(unittest.TestCase):

    def test_proc_no_args(self):
        p = parse_ok(prog('myproc'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s, ProcCallStmt)
        self.assertEqual(s.name, 'myproc')
        self.assertEqual(s.args, [])

    def test_proc_with_args(self):
        p = parse_ok(prog('draw(x, y, color)'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s, ProcCallStmt)
        self.assertEqual(s.name, 'draw')
        self.assertEqual(len(s.args), 3)

    def test_proc_expr_arg(self):
        p = parse_ok(prog('print(a * 2 + 1)'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.args[0], BinOp)


# ---------------------------------------------------------------------------
# 17. With Statement
# ---------------------------------------------------------------------------

class TestWithStatement(unittest.TestCase):

    def test_with_basic(self):
        p = parse_ok(prog('with pt do x := 0'))
        s = p.block.body.stmts[0]
        self.assertIsInstance(s, WithStmt)
        self.assertEqual(len(s.vars), 1)
        self.assertIsInstance(s.vars[0], Var)

    def test_with_multiple_vars(self):
        p = parse_ok(prog('with a, b do x := 0'))
        s = p.block.body.stmts[0]
        self.assertEqual(len(s.vars), 2)

    def test_with_compound(self):
        src = prog('with pt do begin\n  x := 1;\n  y := 2\nend')
        p = parse_ok(src)
        s = p.block.body.stmts[0]
        self.assertIsInstance(s.body, CompoundStmt)


# ---------------------------------------------------------------------------
# 18. Expressions
# ---------------------------------------------------------------------------

class TestExpressions(unittest.TestCase):

    def test_integer_literal(self):
        p = parse_ok(prog('x := 42'))
        self.assertIsInstance(p.block.body.stmts[0].value, IntLit)
        self.assertEqual(p.block.body.stmts[0].value.value, 42)

    def test_real_literal(self):
        p = parse_ok(prog('x := 3.14'))
        self.assertIsInstance(p.block.body.stmts[0].value, RealLit)

    def test_nil_literal(self):
        p = parse_ok(prog('p := nil'))
        self.assertIsInstance(p.block.body.stmts[0].value, NilLit)

    def test_arithmetic_precedence(self):
        # a + b * c  should be  a + (b * c)
        p = parse_ok(prog('x := a + b * c'))
        expr = p.block.body.stmts[0].value
        self.assertIsInstance(expr, BinOp)
        self.assertEqual(expr.op, 'PLUS')
        self.assertIsInstance(expr.right, BinOp)
        self.assertEqual(expr.right.op, 'TIMES')

    def test_parentheses_override_precedence(self):
        # (a + b) * c
        p = parse_ok(prog('x := (a + b) * c'))
        expr = p.block.body.stmts[0].value
        self.assertEqual(expr.op, 'TIMES')
        self.assertIsInstance(expr.left, BinOp)
        self.assertEqual(expr.left.op, 'PLUS')

    def test_unary_minus(self):
        p = parse_ok(prog('x := -n'))
        expr = p.block.body.stmts[0].value
        self.assertIsInstance(expr, UnaryOp)
        self.assertEqual(expr.op, 'MINUS')

    def test_not_operator(self):
        p = parse_ok(prog('x := not flag'))
        expr = p.block.body.stmts[0].value
        self.assertIsInstance(expr, UnaryOp)
        self.assertEqual(expr.op, 'NOT')

    def test_relational_operators(self):
        ops = [
            ('x := a = b',   'EQUALS'),
            ('x := a <> b',  'NEQ'),
            ('x := a < b',   'LT'),
            ('x := a > b',   'GT'),
            ('x := a <= b',  'LEQ'),
            ('x := a >= b',  'GEQ'),
        ]
        for src, expected_op in ops:
            with self.subTest(op=expected_op):
                p = parse_ok(prog(src))
                expr = p.block.body.stmts[0].value
                self.assertIsInstance(expr, BinOp)
                self.assertEqual(expr.op, expected_op)

    def test_boolean_and(self):
        p = parse_ok(prog('x := a and b'))
        expr = p.block.body.stmts[0].value
        self.assertIsInstance(expr, BinOp)
        self.assertEqual(expr.op, 'AND')

    def test_boolean_or(self):
        p = parse_ok(prog('x := a or b'))
        expr = p.block.body.stmts[0].value
        self.assertEqual(expr.op, 'OR')

    def test_div_mod(self):
        p = parse_ok(prog('x := a div b;\ny := a mod b'))
        stmts = p.block.body.stmts
        self.assertEqual(stmts[0].value.op, 'DIV')
        self.assertEqual(stmts[1].value.op, 'MOD')

    def test_function_call_expression(self):
        p = parse_ok(prog('x := sqrt(n)'))
        expr = p.block.body.stmts[0].value
        self.assertIsInstance(expr, FuncCall)
        self.assertEqual(expr.name, 'sqrt')
        self.assertEqual(len(expr.args), 1)

    def test_function_call_multiple_args(self):
        p = parse_ok(prog('x := max(a, b, c)'))
        expr = p.block.body.stmts[0].value
        self.assertEqual(len(expr.args), 3)

    def test_in_operator(self):
        p = parse_ok(prog('x := c in charset'))
        expr = p.block.body.stmts[0].value
        self.assertIsInstance(expr, BinOp)
        self.assertEqual(expr.op, 'IN')

    def test_nested_function_calls(self):
        p = parse_ok(prog('x := f(g(a), h(b))'))
        expr = p.block.body.stmts[0].value
        self.assertIsInstance(expr, FuncCall)
        self.assertIsInstance(expr.args[0], FuncCall)

    def test_complex_expression(self):
        p = parse_ok(prog('x := (a + b) * c - d div 2'))
        expr = p.block.body.stmts[0].value
        # Top: MINUS
        self.assertEqual(expr.op, 'MINUS')

    def test_array_access_in_expression(self):
        p = parse_ok(prog('x := arr[i + 1]'))
        expr = p.block.body.stmts[0].value
        self.assertIsInstance(expr, IndexVar)

    def test_field_access_in_expression(self):
        p = parse_ok(prog('x := pt.y'))
        expr = p.block.body.stmts[0].value
        self.assertIsInstance(expr, FieldVar)
        self.assertEqual(expr.field_name, 'y')

    def test_deref_in_expression(self):
        p = parse_ok(prog('x := p^'))
        expr = p.block.body.stmts[0].value
        self.assertIsInstance(expr, DerefVar)


# ---------------------------------------------------------------------------
# 19. Complex Programs
# ---------------------------------------------------------------------------

class TestComplexPrograms(unittest.TestCase):

    def test_factorial(self):
        src = """\
program Factorial;
var n, result: integer;

function fact(x: integer): integer;
begin
  if x <= 1 then
    fact := 1
  else
    fact := x * fact(x - 1)
end;

begin
  n := 5;
  result := fact(n);
  writeln(result)
end.
"""
        p = parse_ok(src)
        self.assertEqual(p.name, 'Factorial')
        self.assertEqual(len(p.block.vars), 1)
        self.assertEqual(len(p.block.subprograms), 1)
        fn = p.block.subprograms[0]
        self.assertIsInstance(fn, FuncDecl)
        self.assertEqual(fn.name, 'fact')

    def test_bubble_sort(self):
        src = """\
program BubbleSort;
const maxn = 10;
type arr = array[1..10] of integer;
var a: arr;
    i, j, tmp, n: integer;
begin
  n := maxn;
  for i := 1 to n do
    for j := 1 to n - 1 do
      if a[j] > a[j + 1] then begin
        tmp := a[j];
        a[j] := a[j + 1];
        a[j + 1] := tmp
      end
end.
"""
        p = parse_ok(src)
        self.assertEqual(len(p.block.consts), 1)
        self.assertEqual(len(p.block.types), 1)
        self.assertEqual(len(p.block.vars), 2)

    def test_hello_world(self):
        src = """\
program HelloWorld;
begin
  writeln('Hello, World!')
end.
"""
        p = parse_ok(src)
        stmts = p.block.body.stmts
        self.assertEqual(len(stmts), 1)
        self.assertIsInstance(stmts[0], WritelnStmt)

    def test_record_program(self):
        src = """\
program RecordTest;
type point = record x: real; y: real end;
var p: point;
begin
  p.x := 3.0;
  p.y := 4.0;
  writeln(p.x)
end.
"""
        p = parse_ok(src)
        self.assertEqual(len(p.block.types), 1)
        stmts = p.block.body.stmts
        self.assertEqual(len(stmts), 3)
        self.assertIsInstance(stmts[0].target, FieldVar)

    def test_gcd_with_repeat(self):
        src = """\
program GCD;
var a, b: integer;
begin
  a := 48;
  b := 18;
  repeat
    if a > b then
      a := a - b
    else
      b := b - a
  until a = b;
  writeln(a)
end.
"""
        p = parse_ok(src)
        stmts = p.block.body.stmts
        # a := 48, b := 18, repeat, writeln
        self.assertEqual(len(stmts), 4)
        self.assertIsInstance(stmts[2], RepeatStmt)


# ---------------------------------------------------------------------------
# 20. Parse Errors
# ---------------------------------------------------------------------------

class TestParseErrors(unittest.TestCase):
    """Error cases: ParseResult.ok is False and parse_errors is non-empty."""

    # ---- Program-level errors ----

    def test_missing_program_keyword(self):
        r = parse_err("Test;\nbegin\nend.\n")
        self.assertTrue(r.parse_errors)
        self.assertEqual(r.parse_errors[0].kind, 'syntax_error')

    def test_missing_program_name(self):
        r = parse_err("program ;\nbegin\nend.\n")
        self.assertTrue(r.parse_errors)

    def test_missing_semicolon_after_name(self):
        r = parse_err("program Test\nbegin\nend.\n")
        self.assertTrue(r.parse_errors)

    def test_missing_final_dot(self):
        r = parse_err("program Test;\nbegin\nend\n")
        self.assertTrue(r.parse_errors)

    def test_missing_begin(self):
        r = parse_err("program Test;\n  x := 1\nend.\n")
        self.assertTrue(r.parse_errors)

    def test_missing_end(self):
        r = parse_err("program Test;\nbegin\n  x := 1\n.\n")
        self.assertTrue(r.parse_errors)

    # ---- Const errors ----

    def test_const_missing_equals(self):
        r = parse_err(prog(decls='const maxn 100;\n'))
        self.assertTrue(r.parse_errors)

    def test_const_missing_semicolon(self):
        # Without semicolon the parser tries to parse 'b' as another const
        # but sees no '=' → error
        r = parse_err(prog(decls='const a = 1\nb = 2;\n'))
        self.assertTrue(r.parse_errors)

    # ---- Type errors ----

    def test_type_missing_equals(self):
        r = parse_err(prog(decls='type myint integer;\n'))
        self.assertTrue(r.parse_errors)

    def test_type_missing_semicolon(self):
        r = parse_err(prog(decls='type a = integer\nb = real;\n'))
        self.assertTrue(r.parse_errors)

    def test_array_missing_lbracket(self):
        r = parse_err(prog(decls='type a = array 1..10] of integer;\n'))
        self.assertTrue(r.parse_errors)

    def test_array_missing_rbracket(self):
        r = parse_err(prog(decls='type a = array[1..10 of integer;\n'))
        self.assertTrue(r.parse_errors)

    def test_array_missing_of(self):
        r = parse_err(prog(decls='type a = array[1..10] integer;\n'))
        self.assertTrue(r.parse_errors)

    def test_record_missing_end(self):
        r = parse_err(prog(decls='type pt = record x: real; y: real;\n'))
        self.assertTrue(r.parse_errors)

    def test_record_missing_colon(self):
        r = parse_err(prog(decls='type pt = record x real end;\n'))
        self.assertTrue(r.parse_errors)

    def test_set_missing_of(self):
        r = parse_err(prog(decls='type s = set char;\n'))
        self.assertTrue(r.parse_errors)

    def test_file_missing_of(self):
        r = parse_err(prog(decls='type f = file integer;\n'))
        self.assertTrue(r.parse_errors)

    def test_packed_without_structured_type(self):
        r = parse_err(prog(decls='type a = packed integer;\n'))
        self.assertTrue(r.parse_errors)

    # ---- Var errors ----

    def test_var_missing_colon(self):
        r = parse_err(prog(decls='var x integer;\n'))
        self.assertTrue(r.parse_errors)

    def test_var_missing_semicolon(self):
        r = parse_err(prog(decls='var x: integer\ny: real;\n'))
        self.assertTrue(r.parse_errors)

    # ---- Subprogram errors ----

    def test_procedure_missing_name(self):
        r = parse_err(prog(decls='procedure ;\nbegin\nend;\n'))
        self.assertTrue(r.parse_errors)

    def test_procedure_missing_semicolon(self):
        r = parse_err(prog(decls='procedure foo\nbegin\nend;\n'))
        self.assertTrue(r.parse_errors)

    def test_function_missing_colon(self):
        r = parse_err(prog(decls='function f integer;\nbegin\nend;\n'))
        self.assertTrue(r.parse_errors)

    def test_function_missing_return_type(self):
        r = parse_err(prog(decls='function f: ;\nbegin\nend;\n'))
        self.assertTrue(r.parse_errors)

    def test_formal_params_missing_rparen(self):
        r = parse_err(prog(decls='procedure foo(x: integer;\nbegin\nend;\n'))
        self.assertTrue(r.parse_errors)

    def test_formal_params_missing_colon(self):
        r = parse_err(prog(decls='procedure foo(x integer);\nbegin\nend;\n'))
        self.assertTrue(r.parse_errors)

    # ---- Statement errors ----

    def test_if_missing_then(self):
        r = parse_err(prog('if x > 0 y := 1'))
        self.assertTrue(r.parse_errors)

    def test_while_missing_do(self):
        r = parse_err(prog('while x > 0 x := x - 1'))
        self.assertTrue(r.parse_errors)

    def test_for_missing_assign(self):
        r = parse_err(prog('for i 1 to 10 do x := x + 1'))
        self.assertTrue(r.parse_errors)

    def test_for_missing_to_downto(self):
        r = parse_err(prog('for i := 1 10 do x := x + 1'))
        self.assertTrue(r.parse_errors)

    def test_for_missing_do(self):
        r = parse_err(prog('for i := 1 to 10 x := x + 1'))
        self.assertTrue(r.parse_errors)

    def test_repeat_missing_until(self):
        r = parse_err(prog('repeat\n  x := x + 1\nx > 10'))
        self.assertTrue(r.parse_errors)

    def test_case_missing_of(self):
        r = parse_err(prog('case x\n  1: y := 1\nend'))
        self.assertTrue(r.parse_errors)

    def test_case_missing_colon(self):
        r = parse_err(prog('case x of\n  1 y := 1\nend'))
        self.assertTrue(r.parse_errors)

    def test_case_missing_end(self):
        r = parse_err(prog('case x of\n  1: y := 1\n'))
        self.assertTrue(r.parse_errors)

    def test_writeln_missing_rparen(self):
        r = parse_err(prog("writeln('hello'"))
        self.assertTrue(r.parse_errors)

    def test_proc_call_missing_rparen(self):
        r = parse_err(prog('foo(a, b'))
        self.assertTrue(r.parse_errors)

    # ---- Expression errors ----

    def test_expr_missing_rparen(self):
        r = parse_err(prog('x := (a + b'))
        self.assertTrue(r.parse_errors)

    def test_array_index_missing_rbracket(self):
        r = parse_err(prog('arr[i := 0'))
        self.assertTrue(r.parse_errors)

    def test_empty_expression(self):
        r = parse_err(prog('x :='))
        self.assertTrue(r.parse_errors)

    # ---- Error metadata ----

    def test_error_has_line_number(self):
        r = parse_err("program Test;\nbegin\n  if x y := 1\nend.\n")
        self.assertTrue(r.parse_errors)
        self.assertIsInstance(r.parse_errors[0].line, int)
        self.assertGreater(r.parse_errors[0].line, 0)

    def test_error_str_format(self):
        r = parse_err("program Test;\nbegin\nend\n")
        err = r.parse_errors[0]
        s = str(err)
        self.assertIn('[ParseError]', s)
        self.assertIn('syntax_error', s)

    def test_error_has_message(self):
        r = parse_err(prog('if x y := 1'))
        err = r.parse_errors[0]
        self.assertIsInstance(err.message, str)
        self.assertGreater(len(err.message), 0)

    # ---- ParseResult helpers ----

    def test_ok_on_valid(self):
        self.assertTrue(parse(prog()).ok)

    def test_ok_on_invalid(self):
        self.assertFalse(parse("not a program").ok)

    def test_bool_on_valid(self):
        self.assertTrue(bool(parse(prog())))

    def test_bool_on_invalid(self):
        self.assertFalse(bool(parse("bad")))


if __name__ == '__main__':
    unittest.main()
