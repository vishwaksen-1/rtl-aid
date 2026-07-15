// Test various Verilog attribute syntaxes to ensure the fix generalizes
// beyond just `KEEP_FOR_DBG

`define KEEP (*keep*)
`define ASYNC (*async_reset="async"*)

module attr_variants (
  // Simple keep attribute
  (*keep*) input clk,

  // Multiple attributes on same port
  (*mark_debug="true"*) (*keep*) input rst,

  // Attribute with commas inside (the core issue)
  (*mark_debug="true", keep, async_reset="async"*) input wire data_in,

  // Macro-expanded attribute
  `KEEP input wire enable,

  // Attribute in middle
  input wire (*some_attr*) addr,

  // Output with attributes
  (*keep*) output wire [7:0] result,

  `ASYNC output reg magic,

  // Complex attribute with multiple values
  (*mark_debug="true", keep, DONT_TOUCH="TRUE"*) output wire valid,

  // No attributes
  input wire simple_port,
  output wire [15:0] wide_output
);
endmodule
