"""
    The MIT License (MIT)

    Copyright (c) 2023 pkjmesra

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

"""
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectTimeout, ReadTimeout

from PKDevTools.classes.Fetcher import fetcher

@pytest.fixture
def tools_instance():
    return fetcher()

def test_fetchCodes_Exception_negative( tools_instance):
    with patch('requests_cache.CachedSession.get') as mock_get:
        mock_get.side_effect = Exception("sqlite3.OperationalError: attempt to write a readonly database")
        result = tools_instance.fetchURL("https://exampl.ecom/someresource/", stream=True,maxNetworkRetryCount=10)
        assert result is None
        1 < mock_get.call_count <= 10

def test_fetchCodes_Exception_fallback_requests( tools_instance):
    with patch('requests_cache.CachedSession.get') as mock_get:
        with patch('requests.get') as mock_fallback_get:
            mock_get.side_effect = Exception("sqlite3.OperationalError: attempt to write a readonly database")
            result = tools_instance.fetchURL("https://exampl.ecom/someresource/", stream=True,maxNetworkRetryCount=10)
            assert result is not None # because mock_fallback_get will be assigned
            mock_fallback_get.assert_called()
            1 < mock_get.call_count <= 10

def test_postURL_positive(tools_instance):
    url = "https://example.com"
    data = {"key": "value"}
    headers = {"Content-Type": "application/json"}
    response = MagicMock()
    response.status_code = 200
    with patch("requests_cache.CachedSession.post", return_value=response) as mock_post:
        result = tools_instance.postURL(url, data=data, headers=headers)
        mock_post.assert_called_once_with(url, proxies=None, data=data, headers=headers, timeout=2)
        assert result == response

def test_postURL_connect_timeout(tools_instance):
    url = "https://example.com"
    data = {"key": "value"}
    headers = {"Content-Type": "application/json"}
    with patch("requests_cache.CachedSession.post", side_effect=ConnectTimeout) as mock_post:
        tools_instance.postURL(url, data=data, headers=headers)
        mock_post.assert_called_with(url, proxies=None, data=data, headers=headers, timeout=8)

def test_postURL_read_timeout(tools_instance):
    url = "https://example.com"
    data = {"key": "value"}
    headers = {"Content-Type": "application/json"}
    with patch("requests_cache.CachedSession.post", side_effect=ReadTimeout) as mock_post:
        tools_instance.postURL(url, data=data, headers=headers)
        mock_post.assert_called_with(url, proxies=None, data=data, headers=headers, timeout=8)

def test_postURL_other_exception(tools_instance):
    url = "https://example.com"
    data = {"key": "value"}
    headers = {"Content": "application/json"}
    with patch("requests_cache.CachedSession.post", side_effect=Exception) as mock_post:
        tools_instance.postURL(url, data=data, headers=headers)
        mock_post.assert_called_with(url, proxies=None, data=data, headers=headers, timeout=8)

def test_postURL_retry_connect_timeout(tools_instance):
    url = "https://example.com"
    data = {"key": "value"}
    headers = {"Content-Type": "application/json"}
    response = MagicMock()
    response.status_code = 200
    with patch("requests_cache.CachedSession.post", side_effect=[ConnectTimeout, response]) as mock_post:
        result = tools_instance.postURL(url, data=data, headers=headers)
        mock_post.assert_called_with(url, proxies=None, data=data, headers=headers, timeout=4)
        assert result == response

def test_postURL_retry_read_timeout(tools_instance):
    url = "https://example.com"
    data = {"key": "value"}
    headers = {"Content-Type": "application/json"}
    response = MagicMock()
    response.status_code = 200
    with patch("requests_cache.CachedSession.post", side_effect=[ReadTimeout, response]) as mock_post:
        result = tools_instance.postURL(url, data=data, headers=headers)
        mock_post.assert_called_with(url, proxies=None, data=data, headers=headers, timeout=4)
        assert result == response

def test_postURL_retry_other_exception(tools_instance):
    url = "https://example.com"
    data = {"key": "value"}
    headers = {"Content-Type": "application/json"}
    response = MagicMock()
    response.status_code = 200
    with patch("requests_cache.CachedSession.post", side_effect=[Exception, response]) as mock_post:
        result = tools_instance.postURL(url, data=data, headers=headers)
        mock_post.assert_called_with (url,proxies=None, data=data, headers=headers, timeout=4)
        assert result == response

def test_postURL_retry_max_retries(tools_instance):
    url = "https://example.com"
    data = {"key": "value"}
    headers = {"Content-Type": "application/json"}
    response = MagicMock()
    response.status_code = 200
    with patch("requests_cache.CachedSession.post", side_effect=[ConnectTimeout]):
        with patch("requests.post") as mock_post_later:
            tools_instance.postURL(url, data=data, headers=headers)
            mock_post_later.assert_called_with(url, proxies=None, data=data, headers=headers, timeout=4)


def test_postURL_retry_enable_cache_restart(tools_instance, configManager):
    url = "https://example.com"
    data = {"key": "value"}
    headers = {"Content-Type": "application/json"}
    response = MagicMock()
    response.status_code = 200
    with patch("requests_cache.CachedSession.post", side_effect=[ConnectTimeout, response]):
        with patch("requests_cache.is_installed", return_value=False):
            with patch("PKDevTools.classes.Fetcher.fetcher.restartRequestsCache") as mock_restart_cache:
                tools_instance.postURL(url, data=data, headers=headers, trial=2)
                mock_restart_cache.assert_called_once()
