module data_converter #(
    parameter WIDTH = 32,
    localparam DATA_W = $bits(logic [WIDTH-1:0])
) (
    input logic [WIDTH-1:0] din,
    output logic [DATA_W-1:0] dout
);
endmodule
