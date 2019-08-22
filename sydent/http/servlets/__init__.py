# -*- coding: utf-8 -*-

# Copyright 2014 OpenMarket Ltd
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

import json
import copy


class MatrixRestError(Exception):
    def __init__(self, httpStatus, errcode, error):
        super(Exception, self).__init__(error)
        self.httpStatus = httpStatus
        self.errcode = errcode
        self.error = error


def get_args(request, required_args):
    """
    Helper function to get arguments for an HTTP request.
    Currently takes args from the top level keys of a json object or
    www-form-urlencoded for backwards compatability.
    Returns a tuple (error, args) where if error is non-null,
    the request is malformed. Otherwise, args contains the
    parameters passed.
    """
    args = None
    if (
        request.requestHeaders.hasHeader('Content-Type') and
        request.requestHeaders.getRawHeaders('Content-Type')[0].startswith('application/json')
    ):
        try:
            args = json.load(request.content)
        except ValueError:
            raise MatrixRestError(400, 'M_BAD_JSON', 'Malformed JSON')

    # If we didn't get anything from that, try the request args
    # (riot-web's usage of the ed25519 sign servlet currently involves
    # sending the params in the query string with a json body of 'null')
    if args is None:
        args = copy.copy(request.args)
        # Twisted supplies everything as an array because it's valid to
        # supply the same params multiple times with www-form-urlencoded
        # params. This make it incompatible with the json object though,
        # so we need to convert one of them. Since this is the
        # backwards-compat option, we convert this one.
        for k, v in args.items():
            if isinstance(v, list) and len(v) == 1:
                args[k] = v[0]

    missing = []
    for a in required_args:
        if a not in args:
            missing.append(a)

    if len(missing) > 0:
        request.setResponseCode(400)
        msg = "Missing parameters: "+(",".join(missing))
        raise MatrixRestError(400, 'M_MISSING_PARAMS', msg)

    return args

def jsonwrap(f):
    def inner(*args, **kwargs):
        try:
            return json.dumps(f(*args, **kwargs)).encode("UTF-8")
        except MatrixRestError as e:
            request = args[1]
            request.setResponseCode(e.httpStatus)
            return json.dumps({
                "errcode": e.errcode,
                "error": e.error,
            })
    return inner

def send_cors(request):
    request.setHeader(b"Content-Type", b"application/json")
    request.setHeader("Access-Control-Allow-Origin", "*")
    request.setHeader("Access-Control-Allow-Methods",
                      "GET, POST, PUT, DELETE, OPTIONS")
    request.setHeader("Access-Control-Allow-Headers",
                      "Origin, X-Requested-With, Content-Type, Accept")
