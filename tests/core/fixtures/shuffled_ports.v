// Test that ports are correctly categorized when inputs/outputs are shuffled
// This verifies the stateful direction tracking works correctly

module shuffled_ports (
  input clk,
  output [7:0] data_out,
  input rst,
  output valid,
  input [15:0] addr,
  output reg ready,
  input enable,
  output wire [3:0] status
);
endmodule
