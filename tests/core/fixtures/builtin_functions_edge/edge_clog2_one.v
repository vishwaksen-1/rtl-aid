module edge_clog2_one #(
    parameter DEPTH = 1,
    localparam ADDR_W = $clog2(DEPTH)
) (
    input logic clk
);
endmodule
