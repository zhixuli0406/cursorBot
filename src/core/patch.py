"""
Patch System for CursorBot

Provides:
- Git patch application
- Diff generation
- Code modification utilities
"""

import asyncio
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from ..utils.logger import logger


class PatchStatus(Enum):
    """Patch application status."""
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    REVERTED = "reverted"
    CONFLICT = "conflict"


@dataclass
class PatchResult:
    """Result from patch operation."""
    success: bool
    status: PatchStatus
    message: str
    affected_files: list[str] = field(default_factory=list)
    error: Optional[str] = None
    diff_stats: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "status": self.status.value,
            "message": self.message,
            "affected_files": self.affected_files,
            "error": self.error,
            "diff_stats": self.diff_stats,
        }


@dataclass
class Patch:
    """Represents a patch to apply."""
    id: str
    content: str
    source: str = "unknown"
    created_at: datetime = field(default_factory=datetime.now)
    status: PatchStatus = PatchStatus.PENDING
    result: Optional[PatchResult] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "content_preview": self.content[:200] + "..." if len(self.content) > 200 else self.content,
        }


class PatchManager:
    """
    Manages patch operations for code modifications.
    """
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = workspace_path or os.getcwd()
        self._patches: dict[str, Patch] = {}
        self._history: list[Patch] = []
    
    async def apply_patch(
        self,
        patch_content: str,
        target_path: str = None,
        dry_run: bool = False,
    ) -> PatchResult:
        """
        Apply a patch to the workspace.
        
        Args:
            patch_content: The patch content (unified diff format)
            target_path: Specific file to patch (optional)
            dry_run: Test patch without applying
        
        Returns:
            PatchResult
        """
        import uuid
        
        patch_id = str(uuid.uuid4())[:8]
        patch = Patch(
            id=patch_id,
            content=patch_content,
            source="manual",
        )
        self._patches[patch_id] = patch
        
        try:
            # Write patch to temp file
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".patch",
                delete=False
            ) as f:
                f.write(patch_content)
                patch_file = f.name
            
            # Build git apply command
            cmd = ["git", "apply"]
            
            if dry_run:
                cmd.append("--check")
            
            if target_path:
                cmd.extend(["--include", target_path])
            
            cmd.append(patch_file)
            
            # Execute
            result = await self._run_command(cmd)
            
            # Cleanup
            os.unlink(patch_file)
            
            if result["returncode"] == 0:
                patch.status = PatchStatus.APPLIED
                affected = self._parse_affected_files(patch_content)
                
                patch_result = PatchResult(
                    success=True,
                    status=PatchStatus.APPLIED,
                    message="Patch applied successfully" + (" (dry run)" if dry_run else ""),
                    affected_files=affected,
                    diff_stats=self._parse_diff_stats(patch_content),
                )
            else:
                patch.status = PatchStatus.FAILED
                
                # Check if conflict
                if "patch does not apply" in result.get("stderr", ""):
                    patch.status = PatchStatus.CONFLICT
                
                patch_result = PatchResult(
                    success=False,
                    status=patch.status,
                    message="Failed to apply patch",
                    error=result.get("stderr", "Unknown error"),
                )
            
            patch.result = patch_result
            self._history.append(patch)
            
            return patch_result
            
        except Exception as e:
            patch.status = PatchStatus.FAILED
            patch_result = PatchResult(
                success=False,
                status=PatchStatus.FAILED,
                message="Patch operation failed",
                error=str(e),
            )
            patch.result = patch_result
            return patch_result
    
    async def apply_from_file(
        self,
        patch_path: str,
        dry_run: bool = False,
    ) -> PatchResult:
        """Apply patch from a file."""
        try:
            with open(patch_path, "r") as f:
                content = f.read()
            return await self.apply_patch(content, dry_run=dry_run)
        except Exception as e:
            return PatchResult(
                success=False,
                status=PatchStatus.FAILED,
                message=f"Could not read patch file: {e}",
            )
    
    async def create_patch(
        self,
        staged: bool = False,
        files: list[str] = None,
    ) -> str:
        """
        Create a patch from current changes.
        
        Args:
            staged: Include only staged changes
            files: Specific files to include
        
        Returns:
            Patch content as string
        """
        cmd = ["git", "diff"]
        
        if staged:
            cmd.append("--staged")
        
        if files:
            cmd.append("--")
            cmd.extend(files)
        
        result = await self._run_command(cmd)
        return result.get("stdout", "")
    
    async def revert_patch(self, patch_id: str) -> PatchResult:
        """
        Revert a previously applied patch.
        
        Args:
            patch_id: ID of the patch to revert
        
        Returns:
            PatchResult
        """
        if patch_id not in self._patches:
            return PatchResult(
                success=False,
                status=PatchStatus.FAILED,
                message=f"Patch not found: {patch_id}",
            )
        
        patch = self._patches[patch_id]
        
        if patch.status != PatchStatus.APPLIED:
            return PatchResult(
                success=False,
                status=patch.status,
                message=f"Patch is not in applied state: {patch.status.value}",
            )
        
        # Apply patch in reverse
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".patch",
                delete=False
            ) as f:
                f.write(patch.content)
                patch_file = f.name
            
            cmd = ["git", "apply", "--reverse", patch_file]
            result = await self._run_command(cmd)
            
            os.unlink(patch_file)
            
            if result["returncode"] == 0:
                patch.status = PatchStatus.REVERTED
                return PatchResult(
                    success=True,
                    status=PatchStatus.REVERTED,
                    message="Patch reverted successfully",
                )
            else:
                return PatchResult(
                    success=False,
                    status=PatchStatus.FAILED,
                    message="Failed to revert patch",
                    error=result.get("stderr", ""),
                )
                
        except Exception as e:
            return PatchResult(
                success=False,
                status=PatchStatus.FAILED,
                message="Revert operation failed",
                error=str(e),
            )
    
    async def check_patch(self, patch_content: str) -> PatchResult:
        """Check if a patch can be applied without actually applying it."""
        return await self.apply_patch(patch_content, dry_run=True)
    
    def _parse_affected_files(self, patch_content: str) -> list[str]:
        """Parse affected files from patch content."""
        files = []
        
        # Match diff headers
        pattern = r'^diff --git a/(.+?) b/(.+?)$'
        for match in re.finditer(pattern, patch_content, re.MULTILINE):
            files.append(match.group(2))
        
        return list(set(files))
    
    def _parse_diff_stats(self, patch_content: str) -> dict:
        """Parse diff statistics."""
        additions = len(re.findall(r'^\+[^+]', patch_content, re.MULTILINE))
        deletions = len(re.findall(r'^-[^-]', patch_content, re.MULTILINE))
        files = len(self._parse_affected_files(patch_content))
        
        return {
            "additions": additions,
            "deletions": deletions,
            "files_changed": files,
        }
    
    async def _run_command(self, cmd: list[str]) -> dict:
        """Run a shell command asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_path,
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
            
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
            }
    
    def get_patch(self, patch_id: str) -> Optional[Patch]:
        """Get a patch by ID."""
        return self._patches.get(patch_id)
    
    def get_history(self, limit: int = 20) -> list[dict]:
        """Get patch history."""
        patches = self._history[-limit:] if limit else self._history
        return [p.to_dict() for p in reversed(patches)]
    
    def get_stats(self) -> dict:
        """Get patch statistics."""
        return {
            "total_patches": len(self._patches),
            "applied": sum(1 for p in self._patches.values() if p.status == PatchStatus.APPLIED),
            "failed": sum(1 for p in self._patches.values() if p.status == PatchStatus.FAILED),
            "reverted": sum(1 for p in self._patches.values() if p.status == PatchStatus.REVERTED),
        }


# ============================================
# Utility Functions
# ============================================

def create_simple_patch(
    filename: str,
    old_content: str,
    new_content: str,
) -> str:
    """
    Create a simple unified diff patch.
    
    Args:
        filename: File path
        old_content: Original content
        new_content: New content
    
    Returns:
        Unified diff string
    """
    import difflib
    
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    
    return "".join(diff)


# ============================================
# Global Instance
# ============================================

_patch_manager: Optional[PatchManager] = None


def get_patch_manager(workspace_path: str = None) -> PatchManager:
    """Get the global patch manager instance."""
    global _patch_manager
    if _patch_manager is None or workspace_path:
        _patch_manager = PatchManager(workspace_path)
    return _patch_manager


__all__ = [
    "PatchStatus",
    "PatchResult",
    "Patch",
    "PatchManager",
    "create_simple_patch",
    "get_patch_manager",
]
