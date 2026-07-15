// Fixture for backtick attribute handling in port parsing
// Issue: Lines with `KEEP_FOR_DBG and other backtick-prefixed attributes
// should not pollute port names or truncate bit widths.

`define KEEP_FOR_DBG (*mark_debug="true",DONT_TOUCH="TRUE"*)

module backtick_attrs (
  input clk,
  input rst,

  `KEEP_FOR_DBG input  wire ref_1pps,
  input  wire uart_rx,
  `KEEP_FOR_DBG output wire [3:0] tx_tap_index,
  `KEEP_FOR_DBG output wire signed [15:0] tx_tap_value,

  output wire [31:0] tx_addr,
  output wire [1:0] axi_bresp,

  `KEEP_FOR_DBG input  wire [7:0] debug_data,
  `KEEP_FOR_DBG output wire [15:0] debug_status
);
endmodule
