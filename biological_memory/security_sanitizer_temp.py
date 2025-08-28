#!/usr/bin/env python3
"""
STORY-CS-001: Security Sanitizer Module
Temporary file for proper regex patterns
"""

import re
import uuid
import hashlib
import time
from typing import Dict, Any


class SecuritySanitizer:
    """
    STORY-CS-001: Security Hardening - Credential Exposure Prevention
    Handles sanitization of sensitive data in logs and error contexts
    """
    
    # Sensitive data patterns for detection and masking
    SENSITIVE_PATTERNS = {
        'password': [
            r'password[\'"\s]*[:=][\'"\s]*([^\s\'"]+)',
            r'passwd[\'"\s]*[:=][\'"\s]*([^\s\'"]+)',
            r'pwd[\'"\s]*[:=][\'"\s]*([^\s\'"]+)'
        ],
        'api_key': [
            r'api[_\-]?key[\'"\s]*[:=][\'"\s]*([a-zA-Z0-9\-_]{16,})',
            r'apikey[\'"\s]*[:=][\'"\s]*([a-zA-Z0-9\-_]{16,})',
            r'sk-[a-zA-Z0-9]{20,}',
            r'Bearer\s+([a-zA-Z0-9\-._~+/]+=*)',
        ],
        'token': [
            r'token[\'"\s]*[:=][\'"\s]*([a-zA-Z0-9\-_]{16,})',
            r'access[_\-]?token[\'"\s]*[:=][\'"\s]*([a-zA-Z0-9\-_]{16,})',
            r'refresh[_\-]?token[\'"\s]*[:=][\'"\s]*([a-zA-Z0-9\-_]{16,})',
            r'auth[_\-]?token[\'"\s]*[:=][\'"\s]*([a-zA-Z0-9\-_]{16,})',
        ],
        'connection_string': [
            r'://[^:]+:([^@]+)@',  # Captures password in connection strings
            r'postgres://[^:]+:([^@]+)@',
            r'mysql://[^:]+:([^@]+)@',
            r'mongodb://[^:]+:([^@]+)@'
        ],
        'jwt': [
            r'eyJ[a-zA-Z0-9\-_]+=*\.[a-zA-Z0-9\-_]+=*\.[a-zA-Z0-9\-_]+=*',
        ],
        'secret': [
            r'secret[\'"\s]*[:=][\'"\s]*([^\s\'"]+)',
            r'private[_\-]?key[\'"\s]*[:=][\'"\s]*([^\s\'"]+)',
        ],
        'credit_card': [
            r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
        ],
        'ssn': [
            r'\b\d{3}-\d{2}-\d{4}\b',
            r'\b\d{9}\b'
        ],
        'email': [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ],
        'phone': [
            r'\b\d{3}-\d{3}-\d{4}\b',
            r'\(\d{3}\)\s*\d{3}-\d{4}',
            r'\b\d{10}\b'
        ]
    }
    
    # Sensitive keys to look for in dictionaries
    SENSITIVE_KEYS = {
        'password', 'passwd', 'pwd', 'secret', 'private_key', 'api_key', 'apikey',
        'token', 'access_token', 'refresh_token', 'auth_token', 'session_token',
        'connection_string', 'database_url', 'db_url', 'connection_url',
        'authorization', 'bearer', 'x-api-key', 'x-auth-token',
        'ssn', 'social_security_number', 'credit_card', 'cc_number',
        'private', 'confidential', 'sensitive'
    }
    
    @staticmethod
    def sanitize_string(text: str, preserve_structure: bool = True) -> str:
        """
        Sanitize a string by masking sensitive data patterns
        
        Args:
            text: Input string to sanitize
            preserve_structure: Whether to preserve the structure of masked data
            
        Returns:
            Sanitized string with sensitive data masked
        """
        if not isinstance(text, str):
            text = str(text)
            
        sanitized_text = text
        
        # Apply sensitive patterns
        for pattern_type, patterns in SecuritySanitizer.SENSITIVE_PATTERNS.items():
            for pattern in patterns:
                if preserve_structure:
                    # Replace with masked version preserving length
                    def mask_match(match):
                        if match.groups():
                            # Mask captured group (the sensitive part)
                            sensitive_part = match.group(1)
                            prefix_length = len(sensitive_part) // 4  # Show first 25%
                            if len(sensitive_part) <= 4:
                                return match.group(0).replace(sensitive_part, '*' * len(sensitive_part))
                            else:
                                prefix = sensitive_part[:prefix_length]
                                mask_length = len(sensitive_part) - prefix_length
                                return match.group(0).replace(sensitive_part, f"{prefix}{'*' * mask_length}")
                        else:
                            # Mask entire match
                            return '*' * len(match.group(0))
                    
                    sanitized_text = re.sub(pattern, mask_match, sanitized_text, flags=re.IGNORECASE)
                else:
                    # Replace with generic placeholder
                    sanitized_text = re.sub(pattern, f"[REDACTED_{pattern_type.upper()}]", 
                                          sanitized_text, flags=re.IGNORECASE)
        
        return sanitized_text
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any], preserve_structure: bool = True) -> Dict[str, Any]:
        """
        Recursively sanitize dictionary data
        
        Args:
            data: Dictionary to sanitize
            preserve_structure: Whether to preserve the structure of masked data
            
        Returns:
            Sanitized dictionary
        """
        if not isinstance(data, dict):
            return data
            
        sanitized_data = {}
        
        for key, value in data.items():
            # Check if key is sensitive
            if isinstance(key, str) and key.lower() in SecuritySanitizer.SENSITIVE_KEYS:
                if preserve_structure and isinstance(value, str) and len(value) > 4:
                    # Show first character + asterisks
                    sanitized_data[key] = value[0] + '*' * (len(value) - 1)
                else:
                    sanitized_data[key] = "[REDACTED]"
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized_data[key] = SecuritySanitizer.sanitize_dict(value, preserve_structure)
            elif isinstance(value, list):
                # Sanitize list items
                sanitized_data[key] = [
                    SecuritySanitizer.sanitize_dict(item, preserve_structure) if isinstance(item, dict)
                    else SecuritySanitizer.sanitize_string(str(item), preserve_structure) if isinstance(item, str)
                    else item
                    for item in value
                ]
            elif isinstance(value, str):
                # Sanitize string values
                sanitized_data[key] = SecuritySanitizer.sanitize_string(value, preserve_structure)
            else:
                # Keep non-string, non-dict values as-is
                sanitized_data[key] = value
                
        return sanitized_data
    
    @staticmethod
    def generate_secure_error_id() -> str:
        """
        Generate a cryptographically secure error ID instead of predictable timestamp-based IDs
        
        Returns:
            Secure UUID-based error ID
        """
        # Generate UUID4 (random) and convert to compact format
        error_uuid = uuid.uuid4()
        # Create shorter but still unique ID using hex and timestamp hash
        timestamp_hash = hashlib.sha256(str(int(time.time())).encode()).hexdigest()[:8]
        return f"err_{error_uuid.hex[:16]}_{timestamp_hash}"
    
    @staticmethod
    def sanitize_log_message(message: str) -> str:
        """
        Sanitize log messages to prevent log injection attacks
        
        Args:
            message: Raw log message
            
        Returns:
            Sanitized log message
        """
        if not isinstance(message, str):
            message = str(message)
            
        # Remove/escape characters used for log injection
        sanitized_message = message.replace('\n', '\\n')
        sanitized_message = sanitized_message.replace('\r', '\\r')
        sanitized_message = sanitized_message.replace('\t', '\\t')
        sanitized_message = sanitized_message.replace('\x00', '\\x00')  # Null bytes
        
        # Remove ANSI escape codes that could manipulate terminal output
        ansi_escape = re.compile(r'\x1B(?:[@-Z\-_]|\[[0-?]*[ -/]*[@-~])')
        sanitized_message = ansi_escape.sub('', sanitized_message)
        
        # Apply sensitive data sanitization
        sanitized_message = SecuritySanitizer.sanitize_string(sanitized_message)
        
        # Limit message length to prevent log flooding
        max_length = 2000
        if len(sanitized_message) > max_length:
            sanitized_message = sanitized_message[:max_length] + "... [TRUNCATED]"
            
        return sanitized_message