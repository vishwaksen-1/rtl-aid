// Fixture for the "localparam silently dropped" gap (checklist item 64).
module localp #(
  parameter WIDTH = 8,
  localparam DEPTH = WIDTH*2
)(
  input clk,
  output [WIDTH-1:0] q
);
endmodule
