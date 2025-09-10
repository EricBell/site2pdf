"""
Test configuration and shared fixtures for site2pdf tests
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock
import requests

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)

@pytest.fixture
def mock_response():
    """Create a mock HTTP response"""
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.text = "<html><head><title>Test Page</title></head><body><h1>Test Content</h1><p>This is test content.</p></body></html>"
    response.headers = {'content-type': 'text/html'}
    response.url = "https://example.com/test"
    return response

@pytest.fixture
def sample_config():
    """Default configuration for tests"""
    return {
        'crawling': {
            'max_depth': 3,
            'max_pages': 10,
            'request_delay': 0.1,  # Faster for tests
        },
        'content': {
            'include_menus': False,
            'include_images': True,
        },
        'cache': {
            'enabled': True,
            'compression': False,  # Disable for easier testing
        }
    }

@pytest.fixture
def sample_html_pages():
    """Sample HTML pages for testing"""
    return {
        'homepage': """
        <html>
            <head><title>Home Page</title></head>
            <body>
                <nav class="main-nav">
                    <a href="/docs">Documentation</a>
                    <a href="/about">About</a>
                </nav>
                <main>
                    <h1>Welcome</h1>
                    <p>This is the homepage content.</p>
                </main>
            </body>
        </html>
        """,
        'docs_page': """
        <html>
            <head><title>Documentation</title></head>
            <body>
                <nav class="main-nav">
                    <a href="/">Home</a>
                    <a href="/about">About</a>
                </nav>
                <main>
                    <h1>Documentation</h1>
                    <h2>Getting Started</h2>
                    <p>This is documentation content.</p>
                    <img src="/images/diagram.png" alt="Architecture diagram">
                </main>
            </body>
        </html>
        """,
        'login_page': """
        <html>
            <head><title>Login</title></head>
            <body>
                <form action="/login" method="post">
                    <input type="email" name="email" placeholder="Email">
                    <input type="password" name="password" placeholder="Password">
                    <input type="submit" value="Login">
                </form>
            </body>
        </html>
        """
    }

@pytest.fixture
def mock_auth_session():
    """Mock authentication session"""
    from system_tools.authentication.session_store import AuthSession
    session = AuthSession("https://example.com")
    session.cookies = {
        'session_id': 'abc123',
        'csrf_token': 'xyz789'
    }
    session.headers = {
        'User-Agent': 'Mozilla/5.0 (Test Browser)'
    }
    return session