# Copyright 2021 Matrix.org Foundation C.I.C.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from unittest.mock import patch

from parameterized import parameterized
from sydent.db.invite_tokens import JoinTokenStore
from twisted.trial import unittest

from sydent.users.accounts import Account
from tests.utils import make_request, make_sydent


class StoreInviteTestCase(unittest.TestCase):
    """Tests Sydent's register servlet"""

    def setUp(self) -> None:
        # Create a new sydent
        config = {
            "email": {
                "email.from": "Sydent Validation <noreply@hostname>",
            },
        }
        self.sydent = make_sydent(test_config=config)
        self.sender = "@alice:wonderland"

    def assertDictContains(self, actual_dict, expected_dict, msg=None):
        """Assert that actual_dict contains all key/value pairs from expected_dict.

        Args:
            actual_dict: The dict to check
            expected_dict: Dict containing the key/value pairs that should exist in actual_dict
            msg: Optional message to display on failure
        """
        missing = {}
        mismatched = {}
        for key, expected_value in expected_dict.items():
            if key not in actual_dict:
                missing[key] = expected_value
            elif actual_dict[key] != expected_value:
                mismatched[key] = {
                    "expected": expected_value,
                    "actual": actual_dict[key],
                }

        if missing or mismatched:
            msg = msg or ""
            if missing:
                msg += f"\nMissing expected keys: {missing}"
            if mismatched:
                msg += f"\nMismatched values: {mismatched}"
            self.fail(msg)

    @parameterized.expand(
        [
            ("not@an@email@address",),
            ("Naughty Nigel <perfectly.valid@mail.address>",),
        ]
    )
    def test_invalid_email_returns_400(self, address: str) -> None:
        self.sydent.run()

        with patch("sydent.http.servlets.store_invite_servlet.authV2") as authV2:
            authV2.return_value = Account(self.sender, 0, None)

            request, channel = make_request(
                self.sydent.reactor,
                self.sydent.clientApiHttpServer.factory,
                "POST",
                "/_matrix/identity/v2/store-invite",
                content={
                    "address": address,
                    "medium": "email",
                    "room_id": "!myroom:test",
                    "sender": self.sender,
                },
            )

        self.assertEqual(channel.code, 400, channel.json_body)
        self.assertEqual(
            channel.json_body["errcode"], "M_INVALID_EMAIL", channel.json_body
        )

    def test_valid_email_sends_email(self) -> None:
        """Test that a valid email address results in an email being sent"""
        self.sydent.run()

        with patch("sydent.http.servlets.store_invite_servlet.authV2") as authV2, patch(
            "sydent.http.servlets.store_invite_servlet.sendEmail"
        ) as mock_send_email:
            authV2.return_value = Account(self.sender, 0, None)

            request, channel = make_request(
                self.sydent.reactor,
                self.sydent.clientApiHttpServer.factory,
                "POST",
                "/_matrix/identity/v2/store-invite",
                content={
                    "address": "valid@example.com",
                    "medium": "email",
                    "room_id": "!myroom:test",
                    "sender": self.sender,
                },
            )

        self.assertEqual(channel.code, 200)
        mock_send_email.assert_called_once()

        self.assertEqual(
            mock_send_email.call_args[0][1], "matrix-org/invite_template.eml.j2"
        )
        self.assertEqual(
            mock_send_email.call_args[0][2],
            "valid@example.com",
        )

        self.assertDictContains(
            mock_send_email.call_args[0][3],
            {
                "room_id": "!myroom:test",
                "sender": "@alice:wonderland",
            },
            "Email substitutions dict missing expected values",
        )

    def test_skip_email_flag_skips_sending_email(self) -> None:
        """Test that setting skip_email=True prevents an email from being sent"""
        self.sydent.run()

        with patch("sydent.http.servlets.store_invite_servlet.authV2") as authV2, patch(
            "sydent.http.servlets.store_invite_servlet.sendEmail"
        ) as mock_send_email:
            authV2.return_value = Account(self.sender, 0, None)

            request, channel = make_request(
                self.sydent.reactor,
                self.sydent.clientApiHttpServer.factory,
                "POST",
                "/_matrix/identity/v2/store-invite",
                content={
                    "address": "valid@example.com",
                    "medium": "email",
                    "room_id": "!myroom:test",
                    "sender": self.sender,
                    "skip_email": True,
                },
            )

        self.assertEqual(channel.code, 200)
        mock_send_email.assert_not_called()

        # Verify the invite is still stored even though email wasn't sent
        invites = JoinTokenStore(self.sydent).getTokens("email", "valid@example.com")
        self.assertEqual(len(invites), 1)

    def test_space_id_is_included_in_email(self) -> None:
        """Test that space_id is threaded through our system"""
        self.sydent.run()

        with patch("sydent.http.servlets.store_invite_servlet.authV2") as authV2, patch(
            "sydent.http.servlets.store_invite_servlet.sendEmail"
        ) as mock_send_email:
            authV2.return_value = Account(self.sender, 0, None)

            request, channel = make_request(
                self.sydent.reactor,
                self.sydent.clientApiHttpServer.factory,
                "POST",
                "/_matrix/identity/v2/store-invite",
                content={
                    "address": "valid@example.com",
                    "medium": "email",
                    "room_id": "!myroom:test",
                    "sender": self.sender,
                    "space_id": "!myspace:test",
                    "room_name": "My Room",
                    "space_name": "My Space",
                },
            )

        self.assertEqual(channel.code, 200)
        mock_send_email.assert_called_once()

        self.assertEqual(
            mock_send_email.call_args[0][1], "matrix-org/invite_template.eml.j2"
        )
        self.assertEqual(
            mock_send_email.call_args[0][2],
            "valid@example.com",
        )

        self.assertDictContains(
            mock_send_email.call_args[0][3],
            {
                "room_id": "!myroom:test",
                "sender": "@alice:wonderland",
                "space_id": "!myspace:test",
                "space_name": "My Space",
            },
            "Email substitutions dict missing expected values",
        )

        # Also check that the invite is stored with space_id
        invites = JoinTokenStore(self.sydent).getTokens("email", "valid@example.com")
        self.assertEqual(len(invites), 1)
        self.assertEqual(invites[0]["space_id"], "!myspace:test")
        self.assertEqual(invites[0]["room_id"], "!myroom:test")
