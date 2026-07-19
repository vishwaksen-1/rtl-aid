module complex_calc #(
    parameter DATA_WIDTH = 16,
    localparam ADDR_WIDTH = $clog2($bits(logic [DATA_WIDTH-1:0]))
) (
    input logic clk
);
endmodule
