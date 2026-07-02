// Fixture: generate block with a properly labeled begin/end.
module gen_labeled(input [3:0] a, output [3:0] y);
genvar i;
generate
  for (i = 0; i < 4; i = i + 1) begin : gen_blk
    assign y[i] = a[i];
  end
endgenerate
endmodule
