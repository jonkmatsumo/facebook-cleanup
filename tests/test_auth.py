"""
Unit tests for authentication and session management modules.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.auth.cookie_manager import CookieManager, REQUIRED_COOKIES
from src.auth.session_validator import SessionValidator


@pytest.fixture
def temp_cookie_file(tmp_path):
    """Create a temporary cookie file for testing."""
    cookie_file = tmp_path / "cookies.json"
    return cookie_file


@pytest.fixture
def valid_cookie_data():
    """Valid cookie data structure."""
    return {
        "cookies": [
            {
                "name": "c_user",
                "value": "123456789",
                "domain": ".facebook.com",
                "path": "/"
            },
            {
                "name": "xs",
                "value": "abc123def456",
                "domain": ".facebook.com",
                "path": "/"
            },
            {
                "name": "datr",
                "value": "xyz789",
                "domain": ".facebook.com",
                "path": "/"
            }
        ],
        "origins": []
    }


@pytest.fixture
def invalid_cookie_data():
    """Invalid cookie data structure."""
    return {
        "cookies": [
            {
                "name": "c_user",
                "value": "123456789",
                # Missing domain and path
            }
        ]
    }


class TestCookieManager:
    """Test CookieManager class."""
    
    def test_load_cookies_success(self, temp_cookie_file, valid_cookie_data):
        """Test successful cookie loading."""
        # Write valid cookie data
        with open(temp_cookie_file, 'w') as f:
            json.dump(valid_cookie_data, f)
        
        manager = CookieManager(temp_cookie_file)
        cookies = manager.load_cookies()
        
        assert cookies == valid_cookie_data
        assert manager.cookies_data == valid_cookie_data
    
    def test_load_cookies_file_not_found(self, tmp_path):
        """Test loading non-existent cookie file."""
        cookie_file = tmp_path / "nonexistent.json"
        manager = CookieManager(cookie_file)
        
        with pytest.raises(FileNotFoundError) as exc_info:
            manager.load_cookies()
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_load_cookies_invalid_json(self, temp_cookie_file):
        """Test loading invalid JSON file."""
        with open(temp_cookie_file, 'w') as f:
            f.write("not valid json {")
        
        manager = CookieManager(temp_cookie_file)
        
        with pytest.raises(ValueError) as exc_info:
            manager.load_cookies()
        
        assert "invalid json" in str(exc_info.value).lower()
    
    def test_validate_cookie_format_valid(self, valid_cookie_data):
        """Test validation of valid cookie format."""
        manager = CookieManager(Path("dummy"))
        assert manager.validate_cookie_format(valid_cookie_data) is True
    
    def test_validate_cookie_format_missing_cookies_key(self):
        """Test validation with missing cookies key."""
        manager = CookieManager(Path("dummy"))
        invalid_data = {"origins": []}
        assert manager.validate_cookie_format(invalid_data) is False
    
    def test_validate_cookie_format_cookies_not_list(self):
        """Test validation when cookies is not a list."""
        manager = CookieManager(Path("dummy"))
        invalid_data = {"cookies": "not a list", "origins": []}
        assert manager.validate_cookie_format(invalid_data) is False
    
    def test_validate_cookie_format_missing_fields(self, invalid_cookie_data):
        """Test validation with missing required fields."""
        manager = CookieManager(Path("dummy"))
        assert manager.validate_cookie_format(invalid_cookie_data) is False
    
    def test_check_required_cookies_all_present(self, valid_cookie_data):
        """Test checking required cookies when all are present."""
        manager = CookieManager(Path("dummy"))
        manager.cookies_data = valid_cookie_data
        
        all_present, missing = manager.check_required_cookies()
        
        assert all_present is True
        assert missing == []
    
    def test_check_required_cookies_missing(self, valid_cookie_data):
        """Test checking required cookies when some are missing."""
        manager = CookieManager(Path("dummy"))
        # Remove required cookie
        valid_cookie_data["cookies"] = [
            {"name": "c_user", "value": "123", "domain": ".facebook.com", "path": "/"}
        ]
        manager.cookies_data = valid_cookie_data
        
        all_present, missing = manager.check_required_cookies()
        
        assert all_present is False
        assert "xs" in missing
    
    def test_get_cookie_value_found(self, valid_cookie_data):
        """Test getting cookie value when cookie exists."""
        manager = CookieManager(Path("dummy"))
        manager.cookies_data = valid_cookie_data
        
        value = manager.get_cookie_value("c_user")
        
        assert value == "123456789"
    
    def test_get_cookie_value_not_found(self, valid_cookie_data):
        """Test getting cookie value when cookie doesn't exist."""
        manager = CookieManager(Path("dummy"))
        manager.cookies_data = valid_cookie_data
        
        value = manager.get_cookie_value("nonexistent")
        
        assert value is None
    
    def test_get_storage_state_success(self, valid_cookie_data):
        """Test getting storage state with valid cookies."""
        manager = CookieManager(Path("dummy"))
        manager.cookies_data = valid_cookie_data
        
        storage_state = manager.get_storage_state()
        
        assert storage_state == valid_cookie_data
    
    def test_get_storage_state_not_loaded(self):
        """Test getting storage state when cookies not loaded."""
        manager = CookieManager(Path("dummy"))
        
        with pytest.raises(ValueError) as exc_info:
            manager.get_storage_state()
        
        assert "not loaded" in str(exc_info.value).lower()
    
    def test_get_storage_state_missing_required(self, valid_cookie_data):
        """Test getting storage state when required cookies missing."""
        manager = CookieManager(Path("dummy"))
        # Remove required cookie
        valid_cookie_data["cookies"] = [
            {"name": "other", "value": "123", "domain": ".facebook.com", "path": "/"}
        ]
        manager.cookies_data = valid_cookie_data
        
        with pytest.raises(ValueError) as exc_info:
            manager.get_storage_state()
        
        assert "missing required cookies" in str(exc_info.value).lower()


class TestSessionValidator:
    """Test SessionValidator class."""
    
    def test_check_login_redirect_url_contains_login(self):
        """Test detecting login redirect in URL."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/login.php"
        
        assert validator._check_login_redirect(mock_page) is True
    
    def test_check_login_redirect_url_contains_checkpoint(self):
        """Test detecting checkpoint in URL."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/checkpoint"
        
        assert validator._check_login_redirect(mock_page) is True
    
    def test_check_login_redirect_no_redirect(self):
        """Test when not redirected to login."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"
        mock_page.locator.return_value.count.return_value = 0
        
        assert validator._check_login_redirect(mock_page) is False
    
    def test_check_login_redirect_login_form_present(self):
        """Test detecting login form elements."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"
        
        # Mock locator to return element count > 0
        mock_locator = Mock()
        mock_locator.count.return_value = 1
        mock_page.locator.return_value = mock_locator
        
        assert validator._check_login_redirect(mock_page) is True
    
    def test_detect_2fa_challenge_url(self):
        """Test detecting 2FA challenge in URL."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com/checkpoint"
        
        assert validator._detect_2fa_challenge(mock_page) is True
    
    def test_detect_2fa_challenge_content(self):
        """Test detecting 2FA challenge in page content."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"
        mock_page.content.return_value = "Enter your two-factor authentication code"
        
        assert validator._detect_2fa_challenge(mock_page) is True
    
    def test_detect_2fa_challenge_no_challenge(self):
        """Test when no 2FA challenge present."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"
        mock_page.content.return_value = "Welcome to Facebook"
        
        assert validator._detect_2fa_challenge(mock_page) is False
    
    @patch('src.auth.session_validator.SessionValidator._check_login_redirect')
    @patch('src.auth.session_validator.SessionValidator._detect_2fa_challenge')
    def test_validate_session_success(self, mock_2fa, mock_login):
        """Test successful session validation."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"
        
        mock_2fa.return_value = False
        mock_login.return_value = False
        
        # Mock session indicators check
        with patch.object(validator, '_check_session_indicators', return_value=True):
            is_valid, message = validator.validate_session(mock_page)
            
            assert is_valid is True
            assert "valid" in message.lower()
    
    @patch('src.auth.session_validator.SessionValidator._detect_2fa_challenge')
    def test_validate_session_2fa_challenge(self, mock_2fa):
        """Test session validation with 2FA challenge."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"
        
        mock_2fa.return_value = True
        
        is_valid, message = validator.validate_session(mock_page)
        
        assert is_valid is False
        assert "2fa" in message.lower() or "challenge" in message.lower()
    
    @patch('src.auth.session_validator.SessionValidator._detect_2fa_challenge')
    @patch('src.auth.session_validator.SessionValidator._check_login_redirect')
    def test_validate_session_expired(self, mock_login, mock_2fa):
        """Test session validation with expired session."""
        validator = SessionValidator()
        mock_page = Mock()
        mock_page.url = "https://mbasic.facebook.com"
        
        mock_2fa.return_value = False
        mock_login.return_value = True
        
        is_valid, message = validator.validate_session(mock_page)
        
        assert is_valid is False
        assert "expired" in message.lower() or "login" in message.lower()
    
    def test_validate_session_timeout(self):
        """Test session validation with timeout."""
        validator = SessionValidator()
        mock_page = Mock()
        
        # Mock goto to raise TimeoutError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        mock_page.goto.side_effect = PlaywrightTimeoutError("Timeout")
        
        is_valid, message = validator.validate_session(mock_page)
        
        assert is_valid is False
        assert "timeout" in message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

