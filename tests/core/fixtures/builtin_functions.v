// Test module 1: Basic $clog2 usage
module addr_decoder #(
    parameter DEPTH = 256,
    localparam ADDR_W = $clog2(DEPTH)
) (
    input logic clk,
    input logic [ADDR_W-1:0] addr,
    output logic [DEPTH-1:0] decoded
);
endmodule

// Test module 2: $bits usage with typed signal
module data_converter #(
    parameter WIDTH = 32,
    localparam DATA_W = $bits(logic [WIDTH-1:0])
) (
    input logic [WIDTH-1:0] din,
    output logic [DATA_W-1:0] dout
);
endmodule

// Test module 3: $size for array parameter
module fifo_wrapper #(
    parameter int COEFFS[8] = '{1, 2, 3, 4, 5, 6, 7, 8},
    localparam int FIFO_DEPTH = $size(COEFFS)
) (
    input logic clk,
    output logic data
);
endmodule

// Test module 4: $high usage
module memory_controller #(
    parameter ADDR_MAX = 1024,
    localparam TOP_ADDR = $high(ADDR_MAX)
) (
    input logic clk,
    input logic [31:0] addr
);
endmodule

// Test module 5: Nested function calls
module complex_calc #(
    parameter DATA_WIDTH = 16,
    localparam ADDR_WIDTH = $clog2($bits(logic [DATA_WIDTH-1:0]))
) (
    input logic clk
);
endmodule

// Test module 6: $clog2 with edge case N=1
module minimal_decoder #(
    parameter DEPTH = 1,
    localparam ADDR_W = $clog2(DEPTH)
) (
    input logic clk
);
endmodule

// Test module 7: $clog2 with large value
module large_decoder #(
    parameter DEPTH = 65536,
    localparam ADDR_W = $clog2(DEPTH)
) (
    input logic clk
);
endmodule

// Test module 8: Mixed arithmetic and functions
module hybrid_params #(
    parameter BASE_WIDTH = 8,
    parameter MULTIPLIER = 2,
    localparam TOTAL_WIDTH = $bits(logic [BASE_WIDTH * MULTIPLIER - 1:0])
) (
    input logic clk
);
endmodule

// Test module 9: $high with parameter reference
module bounded_mem #(
    parameter MAX_SIZE = 4096,
    localparam BOUND = $high(MAX_SIZE)
) (
    input logic clk
);
endmodule

// Test module 10: All functions in one module
module comprehensive_test #(
    parameter DEPTH = 512,
    localparam ADDR_W = $clog2(DEPTH),
    localparam BUS_W = $bits(logic [63:0]),
    localparam ARR_SIZE = $size(logic [7:0])
) (
    input logic clk
);
endmodule
