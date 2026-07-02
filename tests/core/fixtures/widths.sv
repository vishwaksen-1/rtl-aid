// Fixture for the "widths/types dropped" gap (checklist items 62, 65, 66).
typedef struct packed {
  logic [7:0] a;
  logic [7:0] b;
} pair_t;

typedef enum logic [1:0] {IDLE, RUN, DONE} state_t;

module widths (
  input  logic         clk,
  input  logic [7:0]   data_in,
  input  pair_t        p,
  input  state_t       st,
  output logic [15:0]  data_out
);
endmodule
