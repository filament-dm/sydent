import unittest
from unittest.mock import patch
from sydent.db.invite_tokens import JoinTokenStore
from sydent.db.valsession import ThreePidValSessionStore
from sydent.users.accounts import Account
from tests.utils import make_request, make_sydent


class ThreepidBinderTestCase(unittest.TestCase):
    """Tests Sydent's threepidbind servlet"""

    def setUp(self) -> None:
        # Create a new sydent
        self.sydent = make_sydent()

        self.test_token = "testingtoken"

        # Inject a fake OpenID token into the database
        cur = self.sydent.db.cursor()
        cur.execute(
            "INSERT INTO accounts (user_id, created_ts, consent_version)"
            "VALUES (?, ?, ?)",
            ("@bob:localhost", 101010101, "asd"),
        )
        cur.execute(
            "INSERT INTO tokens (user_id, token)" "VALUES (?, ?)",
            ("@bob:localhost", self.test_token),
        )

        self.sydent.db.commit()

    def test_bind_success(self) -> None:
        """Test that binding a 3pid works successfully"""
        self.sydent.run()

        # Mock the validated session that would be returned
        mock_session = unittest.mock.Mock()
        mock_session.medium = "email"
        mock_session.address = "test@example.com"

        join_token_store = JoinTokenStore(self.sydent)

        join_token_store.storeToken(
            "email",
            "test@example.com",
            "!someroom:example.com",
            "@alice:localhost",
            "some_reg_token",
            space_id="!somespace:example.com",
        )

        with patch.object(
            ThreePidValSessionStore, "getValidatedSession", return_value=mock_session
        ):
            request, channel = make_request(
                self.sydent.reactor,
                self.sydent.clientApiHttpServer.factory,
                "POST",
                "/_matrix/identity/v2/3pid/bind",
                content={
                    "sid": "123",
                    "client_secret": "abcdef",
                    "mxid": "@bob:localhost",
                },
                access_token=self.test_token,
            )

        self.assertEqual(channel.code, 200, channel.json_body)
        self.assertIn("signatures", channel.json_body)
        self.assertIn("medium", channel.json_body)
        self.assertEqual(channel.json_body["medium"], "email")
        self.assertEqual(channel.json_body["address"], "test@example.com")
        self.assertEqual(channel.json_body["mxid"], "@bob:localhost")

        self.assertEqual(len(channel.json_body["invites"]), 1)

        invite = channel.json_body["invites"][0]
        self.assertEqual(invite["medium"], "email")
        self.assertEqual(invite["address"], "test@example.com")
        self.assertEqual(invite["mxid"], "@bob:localhost")
        self.assertEqual(invite["room_id"], "!someroom:example.com")
        self.assertEqual(invite["sender"], "@alice:localhost")
        self.assertEqual(invite["space_id"], "!somespace:example.com")
        self.assertEqual(invite["token"], "some_reg_token")

        # Check the signed data structure
        signed = invite["signed"]
        self.assertEqual(signed["mxid"], "@bob:localhost")
        self.assertEqual(signed["token"], "some_reg_token")
        self.assertIn("signatures", signed)
        self.assertIn(":test:", signed["signatures"])
        self.assertIn("ed25519:0", signed["signatures"][":test:"])
        self.assertEqual(
            signed["signatures"][":test:"]["ed25519:0"],
            "+rTJrDSJohPVMYzBzoqKUV/Ew6FS8GV5rkgNzxNvuyNf1WG4AkuubBuLyqmVM4F84niOrN7/NwTvEeznbDOMBA",
        )
