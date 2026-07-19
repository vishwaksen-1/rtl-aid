module bounded_mem #(
    parameter MAX_SIZE = 4096,
    localparam BOUND = $high(MAX_SIZE)
) (
    input logic clk
);
endmodule
