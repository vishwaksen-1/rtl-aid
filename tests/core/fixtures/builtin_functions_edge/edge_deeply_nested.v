module edge_deeply_nested #(
    parameter DEPTH = 256,
    localparam COMPLEX = $clog2($bits($clog2(DEPTH)))
) (
    input logic clk
);
endmodule
