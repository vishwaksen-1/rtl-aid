module edge_nested_undefined #(
    parameter WIDTH = 8,
    localparam NESTED = $clog2($bits(UNDEFINED))
) (
    input logic clk
);
endmodule
