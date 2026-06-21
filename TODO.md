# ToDos:

- [x] Auto Lint-tagging utility:
	1. Run basic verilator lint test: (`-Wall` is optional)
		```bash
		verilator --lint-only -Wall module.v
		```
	2. Parse the lint errors/warnings
	3. Tag the lines with lint message comments 
		```verliog
		buggy line; /* Check: xyz */
		```
			(xyz is the first line of the warning message)
	4. Add lines at the top of the file below all header comments added by the user:
		```
		// lint-test: <lint-test-command-with-all-necessary-files-backlinks>
		// tb-test: tba
		* Lookout for wrong tagging bug

		Example:
		-- Warning/Error:
		```
		%Warning-WIDTHEXPAND: rtl/core/ll_utils/rx_ram.v:75:65: Operator EQ expects 32 bits on the LHS, but LHS's VARREF 'axi_awaddr_core' generates 6 bits.
														: ... note: In instance 'rx_ram'
	75 |     assign reset_rd_addr_axi = (slv_reg_wren && axi_awaddr_core == RD_DATA_AXI_REG_IDX);  
		|                                                                 ^~
		```
		-- Tagging:
		```verilog
		assign reset_rd_addr_axi = (slv_reg_wren && axi_awaddr_core == RD_DATA_AXI_REG_IDX);  /* Check: Operator EQ expects 32 bits on the LHS, but LHS's VARREF 'axi_awaddr_core' generates 6 bits. */
		```
		

