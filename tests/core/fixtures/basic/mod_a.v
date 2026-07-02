module mod_a #(
    parameter WIDTH = 8,
    parameter DEPTH = 16
) (
    input clk,
    input rst,
    output reg s_read, s_write,
    inout bus
);
    // instantiated mod_b
    mod_b #(.W(WIDTH)) u_b (
        .clk(clk)
    );

    // self instantiation test
    mod_a u_a_self ();
endmodule
