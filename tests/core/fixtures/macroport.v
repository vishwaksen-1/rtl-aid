// Fixture for the "macro-driven ports silently dropped" gap (checklist item 57).
`define IO_IN input
module macroport(
  `IO_IN clk,
  `IO_IN [7:0] data,
  output valid
);
endmodule
