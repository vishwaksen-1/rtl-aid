module comprehensive_test #(
    parameter DEPTH = 512,
    localparam ADDR_W = $clog2(DEPTH),
    localparam BUS_W = $bits(logic [63:0]),
    localparam ARR_SIZE = $size(logic [7:0])
) (
    input logic clk
);
endmodule
