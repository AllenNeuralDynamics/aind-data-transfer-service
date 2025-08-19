"""Tests server module."""

import asyncio
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path, PurePosixPath
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, call, patch

from aind_data_schema_models.modalities import Modality
from authlib.integrations.starlette_client import OAuthError
from botocore.exceptions import ClientError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.testclient import TestClient
from httpx import AsyncClient, RequestError, Response
from requests import Response
from starlette.requests import Request

from aind_data_transfer_service.configs.platforms_v1 import Platform
from aind_data_transfer_service.server import proxy

# from httpx import Response


class TestProxyServer(IsolatedAsyncioTestCase):
    """Tests proxy server that handles v1 routes."""

    @patch("httpx.AsyncClient.request")
    @patch("fastapi.Request.body")
    async def test_proxy(
        self,
        mock_request_body: AsyncMock,
        mock_async_client_request: AsyncMock,
    ):
        """Tests proxy method."""
        mock_request_body.return_value = {"foo": "bar"}
        mock_response = Response()
        mock_response.status_code = 200
        mock_async_client_request.return_value = mock_response

        response = await proxy(
            request=Request(
                scope={"type": "http", "headers": dict(), "method": "POST"}
            ),
            async_client=AsyncClient(),
            path="/foo",
        )
        self.assertEqual(200, response.status_code)

    @patch("httpx.AsyncClient.request")
    @patch("fastapi.Request.body")
    async def test_proxy_with_error(
        self,
        mock_request_body: AsyncMock,
        mock_async_client_request: AsyncMock,
    ):
        """Tests proxy method when an error occurs."""
        mock_request_body.return_value = {"foo": "bar"}
        mock_async_client_request.side_effect = RequestError("Error!")

        response = await proxy(
            request=Request(
                scope={"type": "http", "headers": dict(), "method": "POST"}
            ),
            async_client=AsyncClient(),
            path="/foo",
        )
        self.assertEqual(500, response.status_code)
