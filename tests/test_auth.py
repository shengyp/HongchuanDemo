import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import auth  # noqa: E402


class AuthTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = auth.DB_PATH
        auth.DB_PATH = Path(self.temp.name) / "app.db"
        auth.init_db()

    def tearDown(self):
        auth.DB_PATH = self.original
        self.temp.cleanup()

    def test_login_and_session(self):
        user = auth.register("researcher", "securepass123")
        self.assertIsNone(auth.verify("researcher", "incorrect"))
        self.assertEqual(auth.verify("researcher", "securepass123"), user)
        token = auth.create_session(user["id"])
        self.assertEqual(auth.get_user(token), user)
        auth.delete_session(token)
        self.assertIsNone(auth.get_user(token))

    def test_conversations_are_private(self):
        alice = auth.register("alice", "securepass123")
        bob = auth.register("bob", "securepass123")
        conversation = auth.save_exchange(alice["id"], None, "请推荐食谱", "推荐豆腐", "knowledge")
        self.assertEqual(len(conversation["messages"]), 2)
        self.assertIsNone(auth.get_conversation(bob["id"], conversation["id"]))
        with self.assertRaises(ValueError):
            auth.save_exchange(bob["id"], conversation["id"], "你好", "回复", "knowledge")

    def test_guest_is_stable_without_known_password(self):
        first = auth.guest_user()
        second = auth.guest_user()
        self.assertEqual(first, second)
        self.assertEqual(first["username"], "guest")


if __name__ == "__main__":
    unittest.main()
