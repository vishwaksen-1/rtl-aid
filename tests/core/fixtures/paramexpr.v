// Fixture for the "parameter expression not resolved" gap (checklist item 63).
module paramexpr #(
  parameter BASE = 4,
  parameter DERIVED = BASE * 2
)(
  input clk
);
endmodule
