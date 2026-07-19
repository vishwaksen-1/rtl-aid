module addr_decoder #(
    parameter DEPTH = 256,
    localparam ADDR_W = $clog2(DEPTH)
) (
    input logic clk,
    input logic [ADDR_W-1:0] addr,
    output logic [DEPTH-1:0] decoded
);
endmodule
