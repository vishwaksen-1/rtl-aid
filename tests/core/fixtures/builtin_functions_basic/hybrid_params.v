module hybrid_params #(
    parameter BASE_WIDTH = 8,
    parameter MULTIPLIER = 2,
    localparam TOTAL_WIDTH = $bits(logic [BASE_WIDTH * MULTIPLIER - 1:0])
) (
    input logic clk
);
endmodule
