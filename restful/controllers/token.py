# -*- coding: utf-8 -*-
# Part of odoo. See LICENSE file for full copyright and licensing details.
import json
import logging

import werkzeug.wrappers

from odoo import http
from ..common import invalid_response, valid_response
from odoo.http import request

_logger = logging.getLogger(__name__)

expires_in = "restful.access_token_expires_in"

class APIToken(http.Controller):
    """."""

    def __init__(self):
        self._token = request.env["api.access_token"]
        self._expires_in = request.env.ref(expires_in).sudo().value

    @http.route("/api/auth/token", methods=["POST"], type="http", auth="none", csrf=False, cors="*")
    def token(self, extension_function=None):
        post = json.loads(request.httprequest.data)
        _token = request.env["api.access_token"]
        params = ["db", "login", "password"]
        params = {key: post.get(key) for key in params if post.get(key)}
        db, username, password = post.get("db"), post.get("login"), post.get("password")
        if not all([db, username, password]):
            # Empty 'db' or 'username' or 'password:
            return invalid_response(400,"参数不全, 请检查参数[db, username, password]")
        user_id = request.env['res.users'].sudo().search([('login','=',username)], limit=1)
        if not user_id:
            return invalid_response(503, "用户不存在")
        try:
            request.session.authenticate(db, username, password)
        except Exception as e:
            # Invalid database:
            info = "数据库, 用户名或密码不正确"
            return invalid_response(404, info)

        uid = request.session.uid
        if not uid:
            info = "用户登录失败, 没有找到对应用户"
            return invalid_response(401, info)
        partner_id = request.env['res.users'].browse(uid).partner_id.id
        # Generate tokens
        access_token = _token.find_one_or_create_token(user_id=uid, create=True)
        # Successful response:
        values = {
            "id": uid,
            "partner_id": partner_id,
            "access_token": access_token,
            "expires_in": self._expires_in,
        }
        extension_data = extension_function(uid) if extension_function else {}
        values.update(extension_data)
        return valid_response(values)
