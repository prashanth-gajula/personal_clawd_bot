# guardrails/guardrails_config.py
"""
Guardrails AI configuration for filesystem operations security
"""

import platform
from pathlib import Path
from typing import Tuple


class FileSystemSecurityGuard:
    """Simple security guard for filesystem operations"""
    
    @staticmethod
    def is_protected_path(file_path: Path) -> bool:
        """Check if path is on C: drive (Windows only)"""
        if platform.system() == "Windows":
            try:
                resolved = file_path.resolve()
                if resolved.drive.upper() in ['C:', 'C']:
                    return True
            except:
                pass
        return False
    
    @staticmethod
    def validate_write_operation(file_path: str, operation: str) -> Tuple[bool, str]:
        """
        Check if write operation is allowed.
        
        Args:
            file_path: Path to validate
            operation: Operation name
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        path = Path(file_path)
        
        if FileSystemSecurityGuard.is_protected_path(path):
            error_msg = f"""
❌ SECURITY GUARD: {operation} operation blocked!

Path: {file_path}
Reason: This path is on C: drive or in a protected system directory.

For security reasons, modifications to C: drive are not allowed.
You can:
- Read files from C: drive ✅
- Modify files on other drives (D:, E:, etc.) ✅

Suggested alternative: Use D: drive or another non-system drive.
"""
            return False, error_msg.strip()
        
        return True, ""