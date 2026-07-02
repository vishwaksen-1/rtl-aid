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


if __name__ == "__main__":
    unittest.main()
