{ lex_errors.pas — errores léxicos deliberados
  Errores esperados:
    L10  [LexError]  illegal_character    — símbolo '#' no válido
    L11  [LexError]  unterminated_string  — string sin cerrar
    L12  [LexError]  unterminated_comment — comentario sin cerrar
}
program LexErrors;

var
  x : integer;

begin
  x := #42;
  x := 'cadena sin cerrar;
  { comentario sin cerrar
end.
