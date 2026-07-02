// Fixture: always @(a) references 'b' which is missing from the sensitivity list.
module sens_incomplete(input a, input b, output reg y);
always @(a) begin
  y = a & b;
end
endmodule
