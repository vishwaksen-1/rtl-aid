module memory_controller #(
    parameter ADDR_MAX = 1024,
    localparam TOP_ADDR = $high(ADDR_MAX)
) (
    input logic clk,
    input logic [31:0] addr
);
endmodule
