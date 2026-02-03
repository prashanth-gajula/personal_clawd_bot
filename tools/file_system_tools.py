# tools/file_system_tools.py
"""
Filesystem tools for the agentic workflow system.
Provides comprehensive file and directory operations with automatic file search capabilities.
SECURITY: Simple C: drive protection - prevents modifications to C: drive.
OPTIMIZATION: Fast search prioritizes user directories (Documents, Desktop, Downloads) and non-C drives.
User is prompted for safe write locations instead of using hardcoded paths.
"""

from langchain_core.tools import tool
from pathlib import Path
import shutil
import os
from typing import List, Optional
import platform


# ============================================================================
# SIMPLE SECURITY GUARD (No external library)
# ============================================================================

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


def check_write_permission(file_path: Path, operation: str) -> tuple[bool, str]:
    """Check if write operation is allowed"""
    if is_protected_path(file_path):
        error_msg = f"""
❌ SECURITY GUARD: {operation} operation blocked!

Path: {file_path}
Reason: This path is on C: drive.

For security reasons, modifications to C: drive are not allowed.
You can:
- Read files from C: drive ✅
- Modify files on other drives (D:, E:, etc.) ✅

Suggested alternative: Use D: drive or another non-system drive.
"""
        return False, error_msg.strip()
    return True, ""


# ============================================================================
# HELPER FUNCTIONS - OPTIMIZED SEARCH
# ============================================================================

def get_search_roots_optimized() -> List[Path]:
    """
    Get optimized search roots - prioritize common user locations for faster search.
    Searches user directories first, then other drives.
    
    Returns:
        List of Path objects representing search roots (prioritized)
    """
    system = platform.system()
    
    if system == "Windows":
        # Priority 1: User directories (fastest - usually takes 2-5 seconds)
        priority_locations = [
            Path.home() / "Documents",
            Path.home() / "Desktop", 
            Path.home() / "Downloads",
            Path.home() / "OneDrive",
            Path.home(),  # User home directory
        ]
        
        # Priority 2: Other drives (D:, E:, etc.) - takes 5-10 seconds
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            drive = Path(f"{letter}:/")
            if drive.exists():
                priority_locations.append(drive)
        
        return [loc for loc in priority_locations if loc and loc.exists()]
    else:  # Linux or macOS
        return [
            Path.home() / "Documents",
            Path.home() / "Desktop",
            Path.home() / "Downloads",
            Path.home(),
        ]


def get_search_roots_full() -> List[Path]:
    """
    Get ALL search roots including C: drive (slow - 60+ seconds).
    Only use when user explicitly requests full system search.
    
    Returns:
        List of all Path objects for comprehensive search
    """
    system = platform.system()
    
    if system == "Windows":
        drives = []
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = Path(f"{letter}:/")
            if drive.exists():
                drives.append(drive)
        return drives
    else:
        return [Path.home(), Path("/")]


def get_search_roots() -> List[Path]:
    """
    Default search roots - uses optimized search (excludes C: drive system folders).
    For full search including C:, use get_search_roots_full()
    """
    return get_search_roots_optimized()


def find_file_by_name(filename: str, max_results: int = 10) -> List[Path]:
    """
    Search for files by name across the filesystem (optimized).
    
    Args:
        filename: Name of the file to search for (can be partial)
        max_results: Maximum number of results to return
        
    Returns:
        List of Path objects matching the filename
    """
    results = []
    search_roots = get_search_roots_optimized()
    
    # Common directories to skip for faster search
    skip_dirs = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv',
        'AppData', 'Application Data', '$Recycle.Bin', 'Windows',
        'System Volume Information', 'ProgramData', '.npm', '.cache',
        'Library', 'Applications', 'System32', 'Program Files',
        'Program Files (x86)', 'PerfLogs', 'Recovery'
    }
    
    for root in search_roots:
        try:
            for path in root.rglob(f"*{filename}*"):
                # Skip if any parent directory is in skip_dirs
                if any(skip_dir in path.parts for skip_dir in skip_dirs):
                    continue
                
                if path.is_file():
                    results.append(path)
                    if len(results) >= max_results:
                        return results
        except (PermissionError, OSError):
            # Skip directories we don't have permission to access
            continue
    
    return results


def find_exact_file(filename: str) -> Optional[Path]:
    """
    Find a file with exact name match (optimized).
    
    Args:
        filename: Exact name of the file
        
    Returns:
        Path object if found, None otherwise
    """
    search_roots = get_search_roots_optimized()
    
    skip_dirs = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv',
        'AppData', 'Application Data', '$Recycle.Bin', 'Windows',
        'System Volume Information', 'ProgramData'
    }
    
    for root in search_roots:
        try:
            for path in root.rglob(filename):
                if any(skip_dir in path.parts for skip_dir in skip_dirs):
                    continue
                if path.is_file():
                    return path
        except (PermissionError, OSError):
            continue
    
    return None


def get_available_drives() -> str:
    """
    Get list of available drives (excluding C:) for user to choose from.
    
    Returns:
        Formatted string of available drives
    """
    if platform.system() != "Windows":
        return "Available locations: Home directory or any custom path"
    
    drives = []
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        drive = Path(f"{letter}:/")
        if drive.exists():
            drives.append(f"{letter}:")
    
    if drives:
        return f"Available drives: {', '.join(drives)}"
    else:
        return "No additional drives found. Please specify a custom path."


def format_file_results(matches: List[Path], pattern: str, full_search: bool) -> str:
    """Helper function to format file search results"""
    result = f"Found {len(matches)} file(s) matching '{pattern}':\n\n"
    
    for i, match in enumerate(matches, 1):
        file_size = match.stat().st_size
        if file_size < 1024:
            size_str = f"{file_size} bytes"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.2f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.2f} MB"
        
        # Check if protected
        is_valid, _ = check_write_permission(match, "check")
        protection = "✅ [FULL ACCESS]" if is_valid else "🔒 [READ-ONLY]"
        
        result += f"{i}. {match} ({size_str}) {protection}\n"
    
    if not full_search:
        result += f"\n💡 Searched common locations only (fast search)."
    else:
        result += f"\n💡 Searched entire system including C: drive (full search)."
    
    return result.strip()


# ============================================================================
# FILESYSTEM TOOLS WITH SIMPLE SECURITY
# ============================================================================

@tool
def read_file(filename: str) -> str:
    """
    Read the contents of a file by searching for it in the filesystem.
    You can provide just the filename (e.g., "config.json") or a partial path.
    READ PERMISSION: Allowed on all drives including C:
    
    Args:
        filename: Name of the file to read (just the filename, no full path needed)
        
    Returns:
        File contents as string
    """
    try:
        # First try exact match
        file_path = find_exact_file(filename)
        
        if not file_path:
            # Try partial match
            matches = find_file_by_name(filename, max_results=5)
            
            if not matches:
                return f"Error: No file matching '{filename}' found in the filesystem"
            
            if len(matches) == 1:
                file_path = matches[0]
            else:
                # Multiple matches found
                result = f"Multiple files found matching '{filename}':\n\n"
                for i, match in enumerate(matches, 1):
                    result += f"{i}. {match}\n"
                result += f"\nPlease specify which file you want to read by providing a more specific name or path."
                return result
        
        # Read the file (NO GUARDRAIL - reading is always allowed)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return f"Successfully read file: {file_path}\n\n{content}"
    except UnicodeDecodeError:
        try:
            # Try reading as binary if UTF-8 fails
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
            return f"Successfully read file (binary): {file_path}\n\n{content}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(filename: str, content: str, destination_path: Optional[str] = None) -> str:
    """
    Write content to a file at a user-specified location.
    WRITE PERMISSION: Blocked on C: drive, allowed on other drives.
    
    Args:
        filename: Name of the file to write
        content: Content to write to the file
        destination_path: Full path where to save the file (e.g., "D:/MyFolder/")
                         If None, will prompt user for location
        
    Returns:
        Success or error message, or prompt for location if not provided
    """
    try:
        # If no destination provided, ask user
        if destination_path is None:
            available_drives = get_available_drives()
            return f"""
⚠️ Destination path required for writing file '{filename}'

{available_drives}

Please provide the full path where you want to save this file.
Example: 
- Windows: "D:/MyProjects/" or "E:/Documents/"
- Linux/Mac: "/home/username/documents/" or "~/projects/"

Call write_file again with the destination_path parameter.
"""
        
        # Create the full file path
        dest_dir = Path(destination_path).expanduser().resolve()
        file_path = dest_dir / filename
        
        # SECURITY CHECK
        is_valid, error_msg = check_write_permission(file_path, "WRITE")
        
        if not is_valid:
            return f"{error_msg}\n\n{get_available_drives()}\n\nPlease choose a different location."
        
        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"✅ Successfully wrote to file: {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def append_to_file(filename: str, content: str) -> str:
    """
    Append content to an existing file by searching for it in the filesystem.
    APPEND PERMISSION: Blocked on C: drive, allowed on other drives.
    
    Args:
        filename: Name of the file to append to
        content: Content to append
        
    Returns:
        Success or error message
    """
    try:
        # Find the file
        file_path = find_exact_file(filename)
        
        if not file_path:
            matches = find_file_by_name(filename, max_results=5)
            
            if not matches:
                return f"Error: No file matching '{filename}' found in the filesystem"
            
            if len(matches) == 1:
                file_path = matches[0]
            else:
                result = f"Multiple files found matching '{filename}':\n\n"
                for i, match in enumerate(matches, 1):
                    result += f"{i}. {match}\n"
                result += f"\nPlease specify which file you want to append to."
                return result
        
        # SECURITY CHECK
        is_valid, error_msg = check_write_permission(file_path, "APPEND")
        
        if not is_valid:
            return error_msg
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(content)
        
        return f"✅ Successfully appended to file: {file_path}"
    except Exception as e:
        return f"Error appending to file: {str(e)}"


@tool
def delete_file(filename: str) -> str:
    """
    Delete a file by searching for it in the filesystem.
    DELETE PERMISSION: Blocked on C: drive, allowed on other drives.
    
    Args:
        filename: Name of the file to delete
        
    Returns:
        Success or error message
    """
    try:
        # Find the file
        file_path = find_exact_file(filename)
        
        if not file_path:
            matches = find_file_by_name(filename, max_results=5)
            
            if not matches:
                return f"Error: No file matching '{filename}' found in the filesystem"
            
            if len(matches) == 1:
                file_path = matches[0]
            else:
                result = f"Multiple files found matching '{filename}':\n\n"
                for i, match in enumerate(matches, 1):
                    result += f"{i}. {match}\n"
                result += f"\nPlease specify which file you want to delete."
                return result
        
        # SECURITY CHECK
        is_valid, error_msg = check_write_permission(file_path, "DELETE")
        
        if not is_valid:
            return error_msg
        
        if file_path.is_dir():
            return f"Error: {file_path} is a directory. Use delete_directory instead"
        
        file_path.unlink()
        return f"✅ Successfully deleted file: {file_path}"
    except Exception as e:
        return f"Error deleting file: {str(e)}"


@tool
def search_files(filename_pattern: str, max_results: int = 20, search_c_drive: bool = False) -> str:
    """
    Search for files by name pattern across the filesystem.
    By default, searches common user locations and other drives (excludes C: system folders).
    SEARCH PERMISSION: Allowed on all drives including C:
    
    Args:
        filename_pattern: Pattern to search for (e.g., "config", "*.txt", "report")
        max_results: Maximum number of results to return (default: 20)
        search_c_drive: If True, includes C: drive system folders in search (slower). Default: False
        
    Returns:
        List of matching files with their full paths
    """
    try:
        results = []
        
        # Choose search scope
        if search_c_drive:
            print(f"[Search] Full system search (including C: drive) - may take 60+ seconds...")
            search_roots = get_search_roots_full()
        else:
            print(f"[Search] Optimized search (user directories + D:/E: drives) - should take 5-10 seconds...")
            search_roots = get_search_roots_optimized()
        
        # Common directories to skip for faster search
        skip_dirs = {
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            'AppData', 'Application Data', '$Recycle.Bin', 'Windows',
            'System Volume Information', 'ProgramData', '.npm', '.cache',
            'Library', 'Applications', 'System32', 'Program Files',
            'Program Files (x86)', 'PerfLogs', 'Recovery'
        }
        
        for root in search_roots:
            try:
                print(f"[Search] Searching in: {root}")
                for path in root.rglob(f"*{filename_pattern}*"):
                    # Skip if any parent directory is in skip_dirs
                    if any(skip_dir in path.parts for skip_dir in skip_dirs):
                        continue
                    
                    if path.is_file():
                        results.append(path)
                        if len(results) >= max_results:
                            return format_file_results(results, filename_pattern, search_c_drive)
            except (PermissionError, OSError):
                continue
            
            if len(results) >= max_results:
                break
        
        if not results:
            if not search_c_drive:
                return f"""
No files matching '{filename_pattern}' found in common locations.

Searched: Documents, Desktop, Downloads, D: & E: drives

Would you like me to search the entire C: drive? (May take 60+ seconds)
"""
            else:
                return f"No files matching '{filename_pattern}' found in the filesystem"
        
        return format_file_results(results, filename_pattern, search_c_drive)
        
    except Exception as e:
        return f"Error searching files: {str(e)}"


@tool
def list_directory(directory_path: str) -> str:
    """
    List all files and directories in a given directory.
    LIST PERMISSION: Allowed on all drives including C:
    
    Args:
        directory_path: Path to the directory to list (can be relative or absolute)
        
    Returns:
        List of files and directories
    """
    try:
        path = Path(directory_path).expanduser().resolve()
        
        if not path.exists():
            return f"Error: Directory {directory_path} does not exist"
        
        if not path.is_dir():
            return f"Error: {directory_path} is not a directory"
        
        items = list(path.iterdir())
        files = [f"📄 {item.name}" for item in items if item.is_file()]
        dirs = [f"📁 {item.name}" for item in items if item.is_dir()]
        
        # Add protection status
        is_valid, _ = check_write_permission(path, "check")
        protection = "✅ [FULL ACCESS]" if is_valid else "🔒 [READ-ONLY]"
        
        result = f"Contents of {path} {protection}:\n\n"
        result += "Directories:\n" + "\n".join(dirs) if dirs else "No directories"
        result += "\n\nFiles:\n" + "\n".join(files) if files else "\nNo files"
        
        return result
    except Exception as e:
        return f"Error listing directory: {str(e)}"


@tool
def create_directory(directory_path: str) -> str:
    """
    Create a new directory at user-specified location.
    CREATE PERMISSION: Blocked on C: drive, allowed on other drives.
    
    Args:
        directory_path: Full path to the directory to create (e.g., "D:/MyFolder/NewDir")
        
    Returns:
        Success or error message
    """
    try:
        if not directory_path:
            return f"""
⚠️ Directory path required

{get_available_drives()}

Please provide the full path for the new directory.
Example:
- Windows: "D:/MyProjects/NewFolder"
- Linux/Mac: "/home/username/projects/newfolder"
"""
        
        path = Path(directory_path).expanduser().resolve()
        
        # SECURITY CHECK
        is_valid, error_msg = check_write_permission(path, "CREATE DIRECTORY")
        
        if not is_valid:
            return f"{error_msg}\n\n{get_available_drives()}"
        
        path.mkdir(parents=True, exist_ok=True)
        return f"✅ Successfully created directory: {path}"
    except Exception as e:
        return f"Error creating directory: {str(e)}"


@tool
def delete_directory(directory_name: str) -> str:
    """
    Delete a directory and all its contents by searching for it.
    DELETE PERMISSION: Blocked on C: drive, allowed on other drives.
    
    Args:
        directory_name: Name of the directory to delete
        
    Returns:
        Success or error message
    """
    try:
        # Search for directory
        search_roots = get_search_roots_optimized()
        skip_dirs = {'Windows', 'System Volume Information', 'ProgramData', 'System32'}
        
        found_dirs = []
        for root in search_roots:
            try:
                for path in root.rglob(directory_name):
                    if any(skip_dir in path.parts for skip_dir in skip_dirs):
                        continue
                    if path.is_dir():
                        found_dirs.append(path)
                        if len(found_dirs) >= 5:
                            break
            except (PermissionError, OSError):
                continue
        
        if not found_dirs:
            return f"Error: Directory '{directory_name}' not found"
        
        if len(found_dirs) > 1:
            result = f"Multiple directories found matching '{directory_name}':\n\n"
            for i, dir_path in enumerate(found_dirs, 1):
                is_valid, _ = check_write_permission(dir_path, "check")
                protection = "✅ [CAN DELETE]" if is_valid else "🔒 [PROTECTED]"
                result += f"{i}. {dir_path} {protection}\n"
            result += f"\nPlease specify which directory you want to delete."
            return result
        
        dir_path = found_dirs[0]
        
        # SECURITY CHECK
        is_valid, error_msg = check_write_permission(dir_path, "DELETE DIRECTORY")
        
        if not is_valid:
            return error_msg
        
        shutil.rmtree(dir_path)
        return f"✅ Successfully deleted directory: {dir_path}"
    except Exception as e:
        return f"Error deleting directory: {str(e)}"


@tool
def move_file(filename: str, destination_path: str) -> str:
    """
    Move or rename a file by searching for it in the filesystem.
    MOVE PERMISSION: Blocked if source is on C: drive.
    
    Args:
        filename: Name of the file to move
        destination_path: Full destination path (e.g., "D:/NewLocation/newname.txt")
        
    Returns:
        Success or error message
    """
    try:
        # Find source file
        source = find_exact_file(filename)
        
        if not source:
            matches = find_file_by_name(filename, max_results=5)
            
            if not matches:
                return f"Error: No file matching '{filename}' found"
            
            if len(matches) == 1:
                source = matches[0]
            else:
                result = f"Multiple files found matching '{filename}':\n\n"
                for i, match in enumerate(matches, 1):
                    is_valid, _ = check_write_permission(match, "check")
                    protection = "✅ [CAN MOVE]" if is_valid else "🔒 [PROTECTED]"
                    result += f"{i}. {match} {protection}\n"
                result += f"\nPlease specify which file you want to move."
                return result
        
        # SECURITY CHECK - Source
        is_valid, error_msg = check_write_permission(source, "MOVE")
        
        if not is_valid:
            return error_msg
        
        destination = Path(destination_path).expanduser().resolve()
        
        # SECURITY CHECK - Destination
        is_valid, error_msg = check_write_permission(destination, "MOVE (destination)")
        
        if not is_valid:
            return f"{error_msg}\n\n{get_available_drives()}"
        
        # Create destination directory if needed
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.move(str(source), str(destination))
        return f"✅ Successfully moved {source} to {destination}"
    except Exception as e:
        return f"Error moving file: {str(e)}"


@tool
def copy_file(filename: str, destination_path: str) -> str:
    """
    Copy a file to a new location by searching for it in the filesystem.
    COPY PERMISSION: Can read from C: drive, but cannot write to C: drive.
    
    Args:
        filename: Name of the file to copy
        destination_path: Full destination path (e.g., "D:/Backup/file.txt")
        
    Returns:
        Success or error message
    """
    try:
        # Find source file
        source = find_exact_file(filename)
        
        if not source:
            matches = find_file_by_name(filename, max_results=5)
            
            if not matches:
                return f"Error: No file matching '{filename}' found"
            
            if len(matches) == 1:
                source = matches[0]
            else:
                result = f"Multiple files found matching '{filename}':\n\n"
                for i, match in enumerate(matches, 1):
                    result += f"{i}. {match}\n"
                result += f"\nPlease specify which file you want to copy."
                return result
        
        destination = Path(destination_path).expanduser().resolve()
        
        # SECURITY CHECK - Destination only (copying FROM C: is allowed)
        is_valid, error_msg = check_write_permission(destination, "COPY (destination)")
        
        if not is_valid:
            return f"{error_msg}\n\n{get_available_drives()}"
        
        # Create destination directory if needed
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(str(source), str(destination))
        return f"✅ Successfully copied {source} to {destination}"
    except Exception as e:
        return f"Error copying file: {str(e)}"


@tool
def get_file_info(filename: str) -> str:
    """
    Get detailed information about a file by searching for it in the filesystem.
    INFO PERMISSION: Allowed on all drives including C:
    
    Args:
        filename: Name of the file
        
    Returns:
        File information including size, type, modification time, and permission status
    """
    try:
        # Find the file
        file_path = find_exact_file(filename)
        
        if not file_path:
            matches = find_file_by_name(filename, max_results=5)
            
            if not matches:
                return f"Error: No file matching '{filename}' found"
            
            if len(matches) == 1:
                file_path = matches[0]
            else:
                result = f"Multiple files found matching '{filename}':\n\n"
                for i, match in enumerate(matches, 1):
                    result += f"{i}. {match}\n"
                result += f"\nPlease specify which file you want info for."
                return result
        
        stat = file_path.stat()
        file_type = "Directory" if file_path.is_dir() else "File"
        size = stat.st_size
        
        # Convert size to human readable format
        if size < 1024:
            size_str = f"{size} bytes"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.2f} KB"
        elif size < 1024 * 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.2f} MB"
        else:
            size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
        
        from datetime import datetime
        modified_time = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        # Add permission status
        is_valid, _ = check_write_permission(file_path, "check")
        permission_status = "✅ FULL ACCESS" if is_valid else "🔒 READ-ONLY (C: drive)"
        
        result = f"""
File Information:
- Name: {file_path.name}
- Full Path: {file_path}
- Type: {file_type}
- Size: {size_str}
- Last Modified: {modified_time}
- Permission: {permission_status}
"""
        
        return result.strip()
    except Exception as e:
        return f"Error getting file info: {str(e)}"


@tool
def search_directories(directory_pattern: str, max_results: int = 20, search_c_drive: bool = False) -> str:
    """
    Search for directories/folders by name pattern across the filesystem.
    By default, searches common user locations (Documents, Desktop, Downloads) and other drives (D:, E:).
    SEARCH PERMISSION: Allowed on all drives including C:
    
    Args:
        directory_pattern: Pattern to search for (e.g., "Resumes", "Projects", "Documents")
        max_results: Maximum number of results to return (default: 20)
        search_c_drive: If True, includes C: drive in search (slower, 60+ seconds). Default: False
        
    Returns:
        List of matching directories with their full paths
    """
    try:
        results = []
        
        # Choose search scope based on parameter
        if search_c_drive:
            print(f"[Search] Full system search (including C: drive) - this may take 60+ seconds...")
            search_roots = get_search_roots_full()
        else:
            print(f"[Search] Optimized search (user directories + D:/E: drives) - should take 5-10 seconds...")
            search_roots = get_search_roots_optimized()
        
        # Common directories to skip for faster search
        skip_dirs = {
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            'AppData', 'Application Data', '$Recycle.Bin', 'Windows',
            'System Volume Information', 'ProgramData', '.npm', '.cache',
            'Library', 'Applications', 'System32', 'Program Files',
            'Program Files (x86)', 'PerfLogs', 'Recovery'
        }
        
        for root in search_roots:
            try:
                print(f"[Search] Searching in: {root}")
                for path in root.rglob(f"*{directory_pattern}*"):
                    # Skip if any parent directory is in skip_dirs
                    if any(skip_dir in path.parts for skip_dir in skip_dirs):
                        continue
                    
                    # Only include directories, not files
                    if path.is_dir():
                        results.append(path)
                        if len(results) >= max_results:
                            break
            except (PermissionError, OSError) as e:
                # Skip directories we don't have permission to access
                continue
            
            if len(results) >= max_results:
                break
        
        if not results:
            if not search_c_drive:
                # Suggest full search if nothing found
                return f"""
No directories matching '{directory_pattern}' found in common locations.

Searched locations:
- Documents, Desktop, Downloads, OneDrive
- D: and E: drives (if they exist)

Would you like me to search the entire C: drive? 
(Note: This may take 60+ seconds)

Or you can:
- Provide a more specific search term
- Tell me the exact location if you know it
"""
            else:
                return f"No directories matching '{directory_pattern}' found in the entire filesystem"
        
        result_text = f"Found {len(results)} directory(ies) matching '{directory_pattern}':\n\n"
        for i, match in enumerate(results, 1):
            # Check if protected
            is_valid, _ = check_write_permission(match, "check")
            protection = "✅ [FULL ACCESS]" if is_valid else "🔒 [READ-ONLY]"
            
            result_text += f"{i}. 📁 {match} {protection}\n"
        
        # Add helpful footer
        if not search_c_drive:
            result_text += f"\n💡 Searched common locations only (fast search)."
        else:
            result_text += f"\n💡 Searched entire system including C: drive (full search)."
        
        return result_text.strip()
    except Exception as e:
        return f"Error searching directories: {str(e)}"


# ============================================================================
# EXPORT ALL TOOLS
# ============================================================================

FILESYSTEM_TOOLS = [
    read_file,
    write_file,
    append_to_file,
    delete_file,
    list_directory,
    create_directory,
    delete_directory,
    move_file,
    copy_file,
    get_file_info,
    search_files,
    search_directories
]