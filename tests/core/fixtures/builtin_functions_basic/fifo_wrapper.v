module fifo_wrapper #(
    parameter int COEFFS[8] = '{1, 2, 3, 4, 5, 6, 7, 8},
    localparam int FIFO_DEPTH = $size(COEFFS)
) (
    input logic clk,
    output logic data
);
endmodule
