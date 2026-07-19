module edge_clog2_zero #(
    parameter DEPTH = 0,
    localparam ADDR_W = $clog2(DEPTH)
) (
    input logic clk
);
endmodule
