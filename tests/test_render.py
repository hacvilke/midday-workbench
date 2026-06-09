import unittest

from agent_core.rich_output_template_tool.render import has_renderable_mermaid, normalize_mermaid_output


class RenderTests(unittest.TestCase):
    def test_valid_mermaid_is_detected(self):
        markdown = "```mermaid\ngraph TD\nA --> B\n```"
        self.assertTrue(has_renderable_mermaid(markdown))

    def test_invalid_mermaid_fence_is_unwrapped(self):
        markdown = "```mermaid\nnot a diagram\n```"
        self.assertEqual(normalize_mermaid_output(markdown), "not a diagram")


if __name__ == "__main__":
    unittest.main()
