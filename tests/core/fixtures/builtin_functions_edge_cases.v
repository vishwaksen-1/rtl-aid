// Edge cases and error scenarios for built-in function testing

// Edge case 1: $clog2(0) - undefined, should show unevaluated
module edge_clog2_zero #(
    parameter DEPTH = 0,
    localparam ADDR_W = $clog2(DEPTH)
) (
    input logic clk
);
endmodule

// Edge case 2: $clog2(1) - should evaluate to 0
module edge_clog2_one #(
    parameter DEPTH = 1,
    localparam ADDR_W = $clog2(DEPTH)
) (
    input logic clk
);
endmodule

// Edge case 3: $clog2 with undefined parameter reference
module edge_undefined_param #(
    localparam ADDR_W = $clog2(UNDEFINED_PARAM)
) (
    input logic clk
);
endmodule

// Edge case 4: $bits with undefined type
module edge_bits_undefined #(
    localparam BUS_W = $bits(undefined_type_t)
) (
    input logic clk
);
endmodule

// Edge case 5: $high with non-numeric argument
module edge_high_invalid #(
    localparam TOP = $high(some_string)
) (
    input logic clk
);
endmodule

// Edge case 6: Nested undefined function
module edge_nested_undefined #(
    parameter WIDTH = 8,
    localparam NESTED = $clog2($bits(UNDEFINED))
) (
    input logic clk
);
endmodule

// Edge case 7: Multiple nesting levels
module edge_deeply_nested #(
    parameter DEPTH = 256,
    localparam COMPLEX = $clog2($bits($clog2(DEPTH)))
) (
    input logic clk
);
endmodule

// Edge case 8: Very large number
module edge_large_value #(
    parameter HUGE = 16777216,  // 2^24
    localparam ADDR_W = $clog2(HUGE)
) (
    input logic clk
);
endmodule

// Edge case 9: Negative parameter (should error)
module edge_negative_param #(
    parameter NEG = -10,
    localparam ADDR_W = $clog2(NEG)
) (
    input logic clk
);
endmodule

// Edge case 10: $clog2 with arithmetic expression
module edge_arithmetic #(
    parameter BASE = 16,
    parameter MULT = 2,
    localparam WIDTH = $clog2(BASE * MULT)
) (
    input logic clk
);
endmodule

// Edge case 11: $size with non-array (should fail gracefully)
module edge_size_non_array #(
    localparam ARR_SIZE = $size(42)
) (
    input logic clk
);
endmodule

// Edge case 12: Custom function that doesn't exist
module edge_custom_nonexistent #(
    localparam RESULT = $nonexistent_custom(10)
) (
    input logic clk
);
endmodule
