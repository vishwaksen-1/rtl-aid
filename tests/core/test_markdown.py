import unittest
import os
import tempfile
from rtl_aid.core import VerilogWikiParser
from tests.support import CORE_FIXTURES


class TestMarkdownGenerationAndLogging(unittest.TestCase):
    def setUp(self):
        self.module_b_path = f"{CORE_FIXTURES}/basic/mod_b.v"

    def test_markdown_generation_and_logging(self):
        with tempfile.TemporaryDirectory() as out_dir:
            parser = VerilogWikiParser([self.module_b_path], verbose=2)
            parser.scan()
            parser.generate_markdown(out_dir)

            md_path = os.path.join(out_dir, "mod_b.md")
            self.assertTrue(os.path.exists(md_path))

            # Check it recognized the file was modified
            self.assertTrue(any(md_path in entry[0] for entry in parser.modified_files))

            # Run again, should not modify
            parser2 = VerilogWikiParser([self.module_b_path])
            parser2.scan()
            parser2.generate_markdown(out_dir)
            self.assertEqual(len(parser2.modified_files), 0)

    def test_markdown_creates_nested_output_directory(self):
        """generate_markdown should create nested output directories."""
        with tempfile.TemporaryDirectory() as tmproot:
            out_dir = os.path.join(tmproot, "docs", "modules", "nested")
            parser = VerilogWikiParser([self.module_b_path], verbose=0)
            parser.scan()
            parser.generate_markdown(out_dir)

            # Directory should be created
            self.assertTrue(os.path.isdir(out_dir))
            # Markdown file should exist
            md_path = os.path.join(out_dir, "mod_b.md")
            self.assertTrue(os.path.exists(md_path))

    def test_markdown_dry_run_no_files_written(self):
        """In dry-run mode, markdown should not be written."""
        with tempfile.TemporaryDirectory() as out_dir:
            parser = VerilogWikiParser([self.module_b_path], verbose=0, dry_run=True)
            parser.scan()
            parser.generate_markdown(out_dir)

            # Output directory should not exist
            self.assertFalse(os.path.exists(os.path.join(out_dir, "mod_b.md")))

    def test_markdown_large_port_list(self):
        """Markdown should correctly list modules with 50+ ports."""
        with tempfile.TemporaryDirectory() as tmproot:
            # Create Verilog file with many ports
            test_file = os.path.join(tmproot, "large.v")
            ports = ", ".join([f"input in{i}" for i in range(30)] + [f"output out{i}" for i in range(20)])
            with open(test_file, "w") as f:
                f.write(f"module large_mod({ports}); endmodule")

            out_dir = os.path.join(tmproot, "docs")
            parser = VerilogWikiParser([test_file], verbose=0)
            parser.scan()
            parser.generate_markdown(out_dir)

            # Read markdown
            md_path = os.path.join(out_dir, "large_mod.md")
            with open(md_path) as f:
                content = f.read()

            # All ports should be listed
            for i in range(30):
                self.assertIn(f"in{i}", content)
            for i in range(20):
                self.assertIn(f"out{i}", content)


if __name__ == "__main__":
    unittest.main()
