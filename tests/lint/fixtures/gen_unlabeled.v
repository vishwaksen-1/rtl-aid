// Fixture: generate block with an unlabeled begin/end.
module gen_unlabeled(input [3:0] a, output [3:0] y);
genvar i;
generate
  for (i = 0; i < 4; i = i + 1) begin
    assign y[i] = a[i];
  end
endgenerate
endmodule
