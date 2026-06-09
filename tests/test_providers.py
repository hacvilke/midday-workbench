import unittest

from agent_core.providers import ChatProvider, Message, ProviderError, ProviderRouter


class FailingStreamProvider(ChatProvider):
    name = "failing"

    def complete(self, messages):
        raise ProviderError("nope")

    def stream(self, messages):
        raise ProviderError("stream nope")
        yield ""


class GoodStreamProvider(ChatProvider):
    name = "good"

    def complete(self, messages):
        return "ok"

    def stream(self, messages):
        yield "hello "
        yield "world"


class ProviderRouterTests(unittest.TestCase):
    def test_stream_with_metadata_records_fallback_attempts(self):
        """Verify streaming fallback keeps detailed provider attempts."""

        router = ProviderRouter([FailingStreamProvider(), GoodStreamProvider()])
        events = list(router.stream_with_metadata([Message("user", "hi")]))
        metadata = events[-1]
        tokens = "".join(str(event.get("token", "")) for event in events if event["type"] == "token")
        self.assertEqual(tokens, "hello world")
        self.assertEqual(metadata["type"], "metadata")
        self.assertEqual(metadata["provider"], "good")
        self.assertTrue(metadata["fallback_used"])
        self.assertEqual([attempt.provider for attempt in metadata["attempts"]], ["failing", "good"])
        self.assertFalse(metadata["attempts"][0].ok)
        self.assertTrue(metadata["attempts"][1].ok)


if __name__ == "__main__":
    unittest.main()
