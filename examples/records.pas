{ records.pas — registros, WITH, arrays, sin errores }
program Records;

type
  Point = record
    x : integer;
    y : integer
  end;

  Polygon = array[1..4] of Point;

var
  p       : Point;
  square  : Polygon;
  i       : integer;

procedure PrintPoint(pt: Point);
begin
  writeln('(', pt.x, ', ', pt.y, ')')
end;

begin
  { Asignar con WITH }
  with p do
  begin
    x := 10;
    y := 20
  end;

  PrintPoint(p);

  { Rellenar cuadrado }
  square[1].x := 0;  square[1].y := 0;
  square[2].x := 1;  square[2].y := 0;
  square[3].x := 1;  square[3].y := 1;
  square[4].x := 0;  square[4].y := 1;

  for i := 1 to 4 do
    PrintPoint(square[i])
end.
