"""
Tests for authentication module.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from evergreen.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
    TokenError,
)
from evergreen.auth.password import hash_password, verify_password
from evergreen.config import settings


# =============================================================================
# Password Tests
# =============================================================================

class TestPassword:
    """Tests for password hashing."""

    def test_hash_password(self):
        """Test password hashing produces different hash."""
        password = "mysecurepassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 20  # bcrypt hashes are long

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "mysecurepassword123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Test verifying wrong password."""
        password = "mysecurepassword123"
        hashed = hash_password(password)
        
        assert verify_password("wrongpassword", hashed) is False

    def test_different_passwords_different_hashes(self):
        """Test that same password produces different hashes (salting)."""
        password = "mysecurepassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Hashes should be different due to random salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


# =============================================================================
# JWT Tests
# =============================================================================

class TestJWT:
    """Tests for JWT token handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = str(uuid4())
        self.tenant_id = uuid4()
        self.email = "test@example.com"
        self.role = "user"

    def test_create_access_token(self):
        """Test creating an access token."""
        token = create_access_token(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            email=self.email,
            role=self.role,
        )
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    def test_decode_access_token(self):
        """Test decoding a valid access token."""
        token = create_access_token(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            email=self.email,
            role=self.role,
        )
        
        data = decode_token(token)
        
        assert data.sub == self.user_id
        assert data.tenant_id == self.tenant_id
        assert data.email == self.email
        assert data.role == self.role
        assert data.token_type == "access"

    def test_create_refresh_token(self):
        """Test creating a refresh token."""
        token = create_refresh_token(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
        )
        
        data = decode_token(token)
        
        assert data.sub == self.user_id
        assert data.token_type == "refresh"

    def test_verify_token_type(self):
        """Test token type verification."""
        access_token = create_access_token(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            email=self.email,
        )
        refresh_token = create_refresh_token(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
        )
        
        access_data = decode_token(access_token)
        refresh_data = decode_token(refresh_token)
        
        assert verify_token_type(access_data, "access") is True
        assert verify_token_type(access_data, "refresh") is False
        assert verify_token_type(refresh_data, "refresh") is True
        assert verify_token_type(refresh_data, "access") is False

    def test_token_expiration_default(self):
        """Test default token expiration."""
        token = create_access_token(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            email=self.email,
        )
        
        data = decode_token(token)
        now = datetime.now(timezone.utc)
        
        # Should expire in ~30 minutes
        time_diff = data.exp - now
        assert timedelta(minutes=29) < time_diff < timedelta(minutes=31)

    def test_token_custom_expiration(self):
        """Test custom token expiration."""
        custom_delta = timedelta(hours=2)
        token = create_access_token(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            email=self.email,
            expires_delta=custom_delta,
        )
        
        data = decode_token(token)
        now = datetime.now(timezone.utc)
        
        # Should expire in ~2 hours
        time_diff = data.exp - now
        assert timedelta(hours=1, minutes=59) < time_diff < timedelta(hours=2, minutes=1)

    def test_decode_invalid_token(self):
        """Test decoding invalid token raises error."""
        with pytest.raises(TokenError):
            decode_token("not.a.valid.token")

    def test_decode_tampered_token(self):
        """Test decoding tampered token raises error."""
        token = create_access_token(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            email=self.email,
        )
        
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        
        with pytest.raises(TokenError):
            decode_token(tampered)


# =============================================================================
# Integration Tests
# =============================================================================

class TestAuthIntegration:
    """Integration tests for auth flow."""

    def test_full_auth_flow(self):
        """Test complete authentication flow."""
        user_id = str(uuid4())
        tenant_id = uuid4()
        email = "user@company.com"
        
        # Create tokens
        access = create_access_token(user_id, tenant_id, email, "admin")
        refresh = create_refresh_token(user_id, tenant_id)
        
        # Decode access token
        access_data = decode_token(access)
        assert access_data.sub == user_id
        assert access_data.tenant_id == tenant_id
        assert access_data.role == "admin"
        
        # Decode refresh token
        refresh_data = decode_token(refresh)
        assert refresh_data.sub == user_id
        assert refresh_data.tenant_id == tenant_id
        
        # Verify types
        assert verify_token_type(access_data, "access")
        assert verify_token_type(refresh_data, "refresh")
