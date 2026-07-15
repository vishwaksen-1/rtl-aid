// Fixture for port width parsing with spaces around colons
// Issue: Port ranges like [7 : 0] with spaces are not fully captured
// Current behavior: Captures only [7 and loses : 0]

module port_width_spaces (
  input clk,
  // Standard format (works)
  input wire [7:0] data_no_spaces,
  // Format with spaces (broken)
  input wire [15 : 0] data_with_spaces,
  input wire [C_WIDTH-1 : 0] param_width_with_spaces,
  // Mixed
  input wire [3:0] addr_no_spaces,
  input wire [ADDR_WIDTH-1 : 0] addr_with_spaces,
  // Output variants
  output wire [7 : 0] result_spaces,
  output wire [31:0] result_no_spaces,
  output wire signed [15 : 0] signed_with_spaces,
  // Parameters in ranges
  output wire [PARAM_A-1 : PARAM_B] complex_with_spaces
);
endmodule
