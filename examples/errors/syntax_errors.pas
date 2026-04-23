{ syntax_errors.pas — errores sintácticos deliberados
  Errores esperados:
    L10  [ParseError]  falta THEN en if-statement
    L13  [ParseError]  falta DO en for-loop
    L16  [ParseError]  falta punto final después de END
}
program SyntaxErrors;

var
  x : integer;

begin
  { falta THEN }
  if x > 0
    x := 1;

  { falta DO }
  for x := 1 to 10
    writeln(x)

  { falta punto final }
end
