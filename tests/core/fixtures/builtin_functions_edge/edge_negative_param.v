module edge_negative_param #(
    parameter NEG = -10,
    localparam ADDR_W = $clog2(NEG)
) (
    input logic clk
);
endmodule
