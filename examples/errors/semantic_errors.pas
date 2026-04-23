{ semantic_errors.pas — errores semánticos deliberados
  Errores esperados:
    L20  [SemanticError]  type_mismatch        — asignar string a integer
    L21  [SemanticError]  type_mismatch        — asignar real a boolean
    L23  [SemanticError]  undeclared_identifier — 'z' no declarado
    L25  [SemanticError]  arity_mismatch       — Suma espera 2 args, recibe 3
}
program SemanticErrors;

var
  n    : integer;
  flag : boolean;

function Suma(a: integer; b: integer): integer;
begin
  Suma := a + b
end;

begin
  n    := 'texto';       { type_mismatch: string -> integer }
  flag := 3.14;          { type_mismatch: real -> boolean }

  n := z + 1;            { undeclared_identifier: z }

  n := Suma(1, 2, 3)     { arity_mismatch: espera 2, recibe 3 }
end.
