"""
Password hashing and verification.

Uses bcrypt for secure password storage.
"""

from passlib.context import CryptContext

# Configure password hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Good balance of security/performance
)


def hash_password(password: str) -> str:
    """
    Hash a password for storage.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to check
        hashed_password: Stored password hash
        
    Returns:
        True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)
