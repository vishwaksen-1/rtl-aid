// Fixture: top module instantiating a submodule whose definition lives in
// fixtures/incdir/, used to prove the rtllint -I flag actually works.
module toppw(input [3:0] a4, output [7:0] y);
sub8 u_sub(.a(a4), .y(y));
endmodule
