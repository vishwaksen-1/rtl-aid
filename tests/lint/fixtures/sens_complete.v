// Fixture: sensitivity list covers every signal read in the block.
module sens_complete(input a, input b, output reg y);
always @(a, b) begin
  y = a & b;
end
endmodule
