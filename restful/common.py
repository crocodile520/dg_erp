"""Common methods"""
import ast
import json
import types
import datetime
import base64
import functools
import os
import werkzeug
import odoo
from odoo import http
from odoo.http import request,Response
import logging
_logger = logging.getLogger(__name__)

def validate_token(func):
    """."""
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        """."""
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Origin, Content-Type, Accept, Authorization',
        }

        if request.httprequest.method == 'OPTIONS':
            # 处理预检请求
            return Response(status=200, headers=headers)
        access_token = request.httprequest.headers.get("access_token") or kwargs.get('access_token') or request.httprequest.headers.get("accept")
        if not access_token:
            return invalid_response(401, "missing access token in request header")
        access_token_data = request.env["api.access_token"].sudo().search([("token", "=", access_token)], order="id DESC", limit=1)
        if (access_token_data.find_one_or_create_token(user_id=access_token_data.user_id.id) != access_token):
            _logger.error(f"==========>>>>>>token seems to have expired or invalid \n rev: {access_token} \n new: {access_token_data.find_one_or_create_token(user_id=access_token_data.user_id.id)}")
            return invalid_response(403, "token seems to have expired or invalid")
        request.session.uid = access_token_data.user_id.id
        request.update_env(user=access_token_data.user_id.id)
        return func(self, *args, **kwargs)

    return wrap

def valid_response(data=None, status=200, msg=""):
    if type(data) == list:
        for data_map in data:
            for (key,value) in data_map.items():
                value_type = type(value)
                if value_type == bytes:
                    data_map[key] = str(value, 'utf-8')
                elif value_type == datetime.datetime:
                    data_map[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                elif value_type == datetime.date:
                    data_map[key] = value.strftime("%Y-%m-%d")
    if type(data) == dict:
        for (key,value) in data.items():
            value_type = type(value)
            if value_type == bytes:
                data[key] = str(value, 'utf-8')
            elif value_type == datetime.datetime:
                data[key] = value.strftime("%Y-%m-%d %H:%M:%S")
            elif value_type == datetime.date:
                data[key] = value.strftime("%Y-%m-%d")
            elif value_type == list:
                for data_map in value:
                    if type(data_map) == dict:
                        for (key, value) in data_map.items():
                            value_type = type(value)
                            if value_type == bytes:
                                data_map[key] = str(value, 'utf-8')
                            elif value_type == datetime.datetime:
                                data_map[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                            elif value_type == datetime.date:
                                data_map[key] = value.strftime("%Y-%m-%d")
    return_data = {"data": data or {}, "msg": msg}
    if type(data) == list:
        return_data = {"data": data or [], "msg": msg}
    response = werkzeug.wrappers.Response(
        status=status,
        content_type="application/json; charset=utf-8",
        response=json.dumps(return_data),
    )
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    response.headers['Access-Control-Max-Age'] = 1000
    response.headers['Access-Control-Allow-Headers'] = 'origin, x-csrftoken, content-type, accept, access_token'
    return response

def invalid_response(status=400, msg=None):
    """Invalid Response
    This will be the return value whenever the server runs into an error
    either from the client or the server."""
    response = werkzeug.wrappers.Response(
        status=status,
        content_type="application/json; charset=utf-8",
        response=json.dumps(
            {
                "msg": str(msg) if msg else "wrong arguments (missing validation)",
            }
        ),
    )
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    response.headers['Access-Control-Max-Age'] = 1000
    response.headers['Access-Control-Allow-Headers'] = 'origin, x-csrftoken, content-type, accept, access_token'
    return response