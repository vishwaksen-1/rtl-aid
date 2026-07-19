module edge_arithmetic #(
    parameter BASE = 16,
    parameter MULT = 2,
    localparam WIDTH = $clog2(BASE * MULT)
) (
    input logic clk
);
endmodule
