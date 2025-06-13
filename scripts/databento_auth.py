#!/usr/bin/env python3
"""
BULLETPROOF Databento API Key Authentication
ZERO TOLERANCE for fake data that could cause trading losses
"""

import os
import sys
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class DatabentoCriticalAuthError(Exception):
    """Critical authentication error that must stop all trading operations"""
    pass

class DatabentoBulletproofAuth:
    """
    Bulletproof API authentication with ZERO tolerance for failures
    Will NEVER allow fake data to pass through
    """

    def __init__(self):
        self.api_key: Optional[str] = None
        self.validated: bool = False
        self.validation_timestamp: Optional[str] = None

    def load_and_validate_api_key(self) -> str:
        """
        Load and validate API key with multiple fallback sources
        FAILS FAST if authentication cannot be established

        Returns:
            str: Validated API key

        Raises:
            DatabentoCriticalAuthError: If authentication fails
        """
        logger.info("🔐 STARTING BULLETPROOF API KEY VALIDATION")

        # 1. Try environment variable first
        api_key = os.getenv('DATABENTO_API_KEY')
        if api_key:
            logger.info(f"✅ Found API key in environment: {api_key[:10]}...")
            success, message = self._validate_api_key(api_key)
            if success:
                self.api_key = api_key
                self.validated = True
                logger.info("✅ Environment API key VALIDATED")
                return api_key
            else:
                logger.error(f"❌ Environment API key INVALID: {message}")

        # 2. Try .env file as fallback
        logger.info("🔄 Trying .env file fallback...")
        env_file_key = self._load_from_env_file()
        if env_file_key:
            logger.info(f"✅ Found API key in .env file: {env_file_key[:10]}...")
            success, message = self._validate_api_key(env_file_key)
            if success:
                self.api_key = env_file_key
                self.validated = True
                logger.info("✅ .env file API key VALIDATED")
                return env_file_key
            else:
                logger.error(f"❌ .env file API key INVALID: {message}")

        # 3. CRITICAL FAILURE - NO VALID API KEY FOUND
        error_msg = (
            "🚨 CRITICAL AUTHENTICATION FAILURE 🚨\n"
            "NO VALID DATABENTO API KEY FOUND!\n"
            "\n"
            "This is a TRADING SAFETY MECHANISM.\n"
            "Using fake data could cause FINANCIAL LOSSES.\n"
            "\n"
            "To fix:\n"
            "1. Get your API key from https://databento.com/\n"
            "2. Set environment variable: export DATABENTO_API_KEY='your-key'\n"
            "3. OR add to .env file: DATABENTO_API_KEY=your-key\n"
            "\n"
            "🛑 TRADING OPERATIONS STOPPED FOR YOUR SAFETY"
        )

        logger.critical(error_msg)
        raise DatabentoCriticalAuthError(error_msg)

    def _load_from_env_file(self) -> Optional[str]:
        """Load API key from .env file"""
        try:
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('DATABENTO_API_KEY='):
                        key = line.split('=', 1)[1].strip()
                        # Remove quotes if present
                        if key.startswith('"') and key.endswith('"'):
                            key = key[1:-1]
                        elif key.startswith("'") and key.endswith("'"):
                            key = key[1:-1]
                        return key
        except FileNotFoundError:
            logger.warning("No .env file found")
        except Exception as e:
            logger.error(f"Error reading .env file: {e}")

        return None

    def _validate_api_key(self, api_key: str) -> Tuple[bool, str]:
        """
        Validate API key by making actual API call

        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        if not api_key:
            return False, "API key is empty"

        if not api_key.startswith('db-'):
            return False, "API key must start with 'db-'"

        if len(api_key) < 20:
            return False, "API key too short"

        # Test actual API connection
        try:
            import databento as db

            logger.info("🧪 Testing API key with live connection...")
            client = db.Historical(api_key)

            # Make a lightweight API call to validate
            datasets = client.metadata.list_datasets()

            if not datasets:
                return False, "API key valid but no datasets accessible"

            # Check for required GLBX access
            has_glbx = any('GLBX' in str(dataset) for dataset in datasets)
            if not has_glbx:
                return False, "API key valid but missing GLBX dataset access"

            logger.info(f"✅ API validation successful - {len(datasets)} datasets, GLBX access confirmed")
            return True, "API key validated successfully"

        except ImportError:
            return False, "databento package not installed"
        except Exception as e:
            return False, f"API validation failed: {e}"

    def get_validated_client(self):
        """
        Get validated databento client

        Returns:
            databento.Historical: Validated client

        Raises:
            DatabentoCriticalAuthError: If not validated
        """
        if not self.validated or not self.api_key:
            raise DatabentoCriticalAuthError(
                "API key not validated! Call load_and_validate_api_key() first!"
            )

        try:
            import databento as db
            return db.Historical(self.api_key)
        except Exception as e:
            raise DatabentoCriticalAuthError(f"Failed to create validated client: {e}")

    def assert_trading_safe(self):
        """
        Assert that the system is safe for trading operations

        Raises:
            DatabentoCriticalAuthError: If not safe for trading
        """
        if not self.validated:
            raise DatabentoCriticalAuthError(
                "🚨 NOT SAFE FOR TRADING: API key not validated!"
            )

        if not self.api_key:
            raise DatabentoCriticalAuthError(
                "🚨 NOT SAFE FOR TRADING: No API key available!"
            )

        logger.info("✅ TRADING SAFETY CONFIRMED - Authentication validated")

# Global singleton for bulletproof auth
_auth_instance = None

def get_bulletproof_auth() -> DatabentoBulletproofAuth:
    """Get the global bulletproof auth instance"""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = DatabentoBulletproofAuth()
    return _auth_instance

def ensure_trading_safe_databento_client():
    """
    Ensure we have a trading-safe databento client

    Returns:
        databento.Historical: Validated client safe for trading

    Raises:
        DatabentoCriticalAuthError: If authentication fails
    """
    auth = get_bulletproof_auth()

    # Load and validate if not already done
    if not auth.validated:
        auth.load_and_validate_api_key()

    # Double-check trading safety
    auth.assert_trading_safe()

    return auth.get_validated_client()

if __name__ == "__main__":
    # Test the bulletproof authentication
    try:
        print("🧪 Testing Bulletproof Authentication...")
        auth = DatabentoBulletproofAuth()
        api_key = auth.load_and_validate_api_key()
        print(f"✅ SUCCESS: API key validated: {api_key[:10]}...")

        client = auth.get_validated_client()
        print("✅ SUCCESS: Validated client created")

        auth.assert_trading_safe()
        print("✅ SUCCESS: System confirmed SAFE FOR TRADING")

    except DatabentoCriticalAuthError as e:
        print(f"🚨 CRITICAL ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        sys.exit(1)
