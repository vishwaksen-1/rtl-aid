module edge_large_value #(
    parameter HUGE = 16777216,
    localparam ADDR_W = $clog2(HUGE)
) (
    input logic clk
);
endmodule
