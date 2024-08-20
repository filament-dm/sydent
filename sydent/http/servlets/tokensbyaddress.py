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


class TokensByAddressServlet(SydentResource):
    isLeaf = True

    def __init__(self, syd: "Sydent") -> None:
        super().__init__()
        self.sydent = syd

    @jsonwrap
    def render_GET(self, request: Request) -> JsonDict:
        """
        Return the tokens associated associated with this address.
        """
        send_cors(request)

        if b"address" not in request.args:
            raise MatrixRestError(400, "M_MISSING_PARAM", "address parameter missing")

        address = request.args[b"address"][0].decode("utf-8")
        if b"medium" in request.args:
            medium = request.args[b"medium"][0].decode("utf-8")
        else:
            medium = "email"

        cur = self.sydent.db.cursor()
        res = cur.execute(
            "select sender, room_id, token FROM invite_tokens WHERE address = ? AND medium = ?",
            (address, medium),
        )

        rows = res.fetchall()

        return [{"sender": row[0], "room_id": row[1], "token": row[2]} for row in rows]

    def render_OPTIONS(self, request: Request) -> bytes:
        send_cors(request)
        return b""
