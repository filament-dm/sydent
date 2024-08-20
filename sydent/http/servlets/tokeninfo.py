# Copyright 2019 The Matrix.org Foundation C.I.C.
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

import logging
from typing import TYPE_CHECKING

from twisted.web.server import Request

from sydent.http.auth import authV2
from sydent.http.servlets import MatrixRestError, SydentResource, jsonwrap, send_cors
from sydent.types import JsonDict

if TYPE_CHECKING:
    from sydent.sydent import Sydent

logger = logging.getLogger(__name__)


class TokenInfoServlet(SydentResource):
    isLeaf = True

    def __init__(self, syd: "Sydent") -> None:
        super().__init__()
        self.sydent = syd

    @jsonwrap
    def render_GET(self, request: Request) -> JsonDict:
        """
        Return the email address associated with this invite token,
        fail if the token is not found.
        """
        send_cors(request)

        token = request.args[b"token"][0].decode("utf-8")

        cur = self.sydent.db.cursor()
        res = cur.execute(
            "select medium, address, sender, room_id FROM invite_tokens WHERE token = ?",
            (token,),
        )

        row = res.fetchone()

        if row is None:
            raise MatrixRestError(403, "M_UNAUTHORIZED", "Invite not found")

        return {
            "medium": row[0],
            "address": row[1],
            "sender": row[2],
            "room_id": row[3],
        }

    def render_OPTIONS(self, request: Request) -> bytes:
        send_cors(request)
        return b""
