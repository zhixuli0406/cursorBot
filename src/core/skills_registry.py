"""
Skills Registry for CursorBot

Provides:
- Remote skill discovery and search
- Automatic skill installation
- Skill versioning and updates
- Built-in skill repository

Usage:
    from src.core.skills_registry import get_skills_registry
    
    registry = get_skills_registry()
    
    # Search for skills
    results = await registry.search("web scraping")
    
    # Install a skill
    await registry.install("web-scraper")
    
    # List installed skills
    installed = await registry.list_installed()
"""

import os
import json
import asyncio
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

import httpx

from ..utils.logger import logger


@dataclass
class SkillManifest:
    """Skill manifest definition."""
    id: str
    name: str
    description: str
    version: str
    author: str = ""
    tags: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    repository: str = ""
    homepage: str = ""
    license: str = "MIT"
    min_version: str = "0.1.0"
    created_at: str = ""
    updated_at: str = ""
    downloads: int = 0
    rating: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "commands": self.commands,
            "dependencies": self.dependencies,
            "repository": self.repository,
            "homepage": self.homepage,
            "license": self.license,
            "min_version": self.min_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "downloads": self.downloads,
            "rating": self.rating,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SkillManifest":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            tags=data.get("tags", []),
            commands=data.get("commands", []),
            dependencies=data.get("dependencies", []),
            repository=data.get("repository", ""),
            homepage=data.get("homepage", ""),
            license=data.get("license", "MIT"),
            min_version=data.get("min_version", "0.1.0"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            downloads=data.get("downloads", 0),
            rating=data.get("rating", 0.0),
        )


@dataclass
class InstalledSkill:
    """Represents an installed skill."""
    manifest: SkillManifest
    path: Path
    installed_at: datetime
    enabled: bool = True
    
    def to_dict(self) -> dict:
        return {
            "manifest": self.manifest.to_dict(),
            "path": str(self.path),
            "installed_at": self.installed_at.isoformat(),
            "enabled": self.enabled,
        }


# Built-in skills catalog
BUILTIN_SKILLS: list[SkillManifest] = [
    SkillManifest(
        id="web-search",
        name="Web Search",
        description="Search the web using DuckDuckGo or Google",
        version="1.0.0",
        author="CursorBot",
        tags=["search", "web", "research"],
        commands=["/search", "/google", "/ddg"],
    ),
    SkillManifest(
        id="code-analysis",
        name="Code Analysis",
        description="Analyze code quality, complexity, and security",
        version="1.0.0",
        author="CursorBot",
        tags=["code", "analysis", "security"],
        commands=["/analyze", "/lint", "/security-scan"],
    ),
    SkillManifest(
        id="file-manager",
        name="File Manager",
        description="File operations: read, write, copy, move, delete",
        version="1.0.0",
        author="CursorBot",
        tags=["file", "filesystem", "io"],
        commands=["/file", "/ls", "/cat", "/cp", "/mv", "/rm"],
    ),
    SkillManifest(
        id="git-helper",
        name="Git Helper",
        description="Git operations: status, commit, push, pull, branch",
        version="1.0.0",
        author="CursorBot",
        tags=["git", "vcs", "version-control"],
        commands=["/git", "/commit", "/push", "/pull", "/branch"],
    ),
    SkillManifest(
        id="translator",
        name="Translator",
        description="Translate text between languages",
        version="1.0.0",
        author="CursorBot",
        tags=["translate", "language", "i18n"],
        commands=["/translate", "/tr"],
    ),
    SkillManifest(
        id="calculator",
        name="Calculator",
        description="Mathematical calculations and conversions",
        version="1.0.0",
        author="CursorBot",
        tags=["math", "calculator", "convert"],
        commands=["/calc", "/convert", "/math"],
    ),
    SkillManifest(
        id="reminder",
        name="Reminder",
        description="Set reminders and notifications",
        version="1.0.0",
        author="CursorBot",
        tags=["reminder", "notification", "schedule"],
        commands=["/remind", "/reminder", "/notify"],
    ),
    SkillManifest(
        id="weather",
        name="Weather",
        description="Get weather information and forecasts",
        version="1.0.0",
        author="CursorBot",
        tags=["weather", "forecast", "climate"],
        commands=["/weather", "/forecast"],
    ),
    SkillManifest(
        id="screenshot",
        name="Screenshot",
        description="Take screenshots of web pages",
        version="1.0.0",
        author="CursorBot",
        tags=["screenshot", "web", "capture"],
        commands=["/screenshot", "/capture"],
    ),
    SkillManifest(
        id="json-tools",
        name="JSON Tools",
        description="Parse, format, and query JSON data",
        version="1.0.0",
        author="CursorBot",
        tags=["json", "data", "format"],
        commands=["/json", "/jq", "/format-json"],
    ),
    SkillManifest(
        id="markdown-tools",
        name="Markdown Tools",
        description="Convert and render Markdown",
        version="1.0.0",
        author="CursorBot",
        tags=["markdown", "document", "convert"],
        commands=["/md", "/markdown", "/md2html"],
    ),
    SkillManifest(
        id="image-tools",
        name="Image Tools",
        description="Resize, convert, and optimize images",
        version="1.0.0",
        author="CursorBot",
        tags=["image", "resize", "convert"],
        commands=["/image", "/resize", "/compress"],
    ),
    SkillManifest(
        id="crypto-tools",
        name="Crypto Tools",
        description="Encrypt, decrypt, hash, and encode data",
        version="1.0.0",
        author="CursorBot",
        tags=["crypto", "encrypt", "hash"],
        commands=["/encrypt", "/decrypt", "/hash", "/base64"],
    ),
    SkillManifest(
        id="api-tester",
        name="API Tester",
        description="Test REST APIs with HTTP requests",
        version="1.0.0",
        author="CursorBot",
        tags=["api", "http", "rest", "test"],
        commands=["/http", "/get", "/post", "/api"],
    ),
    SkillManifest(
        id="db-query",
        name="Database Query",
        description="Query databases (SQLite, PostgreSQL, MySQL)",
        version="1.0.0",
        author="CursorBot",
        tags=["database", "sql", "query"],
        commands=["/sql", "/query", "/db"],
    ),
]


class SkillsRegistry:
    """
    Skills registry for discovering and installing skills.
    
    Provides:
    - Local built-in skill catalog
    - Remote skill discovery (if registry URL configured)
    - Skill installation and updates
    - Version management
    """
    
    # Default registry URL (can be overridden)
    DEFAULT_REGISTRY_URL = "https://registry.cursorbot.dev/api/v1"
    
    def __init__(
        self,
        skills_dir: Path = None,
        registry_url: str = None,
    ):
        """
        Initialize the skills registry.
        
        Args:
            skills_dir: Directory for installed skills
            registry_url: Remote registry API URL
        """
        self.skills_dir = skills_dir or Path(__file__).parent.parent.parent / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        self.registry_url = registry_url or os.getenv(
            "SKILLS_REGISTRY_URL",
            self.DEFAULT_REGISTRY_URL
        )
        
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "skills"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.installed_file = self.data_dir / "installed.json"
        
        self._installed_skills: dict[str, InstalledSkill] = {}
        self._load_installed()
    
    def _load_installed(self) -> None:
        """Load installed skills from disk."""
        if self.installed_file.exists():
            try:
                with open(self.installed_file) as f:
                    data = json.load(f)
                
                for skill_id, info in data.items():
                    manifest = SkillManifest.from_dict(info.get("manifest", {}))
                    self._installed_skills[skill_id] = InstalledSkill(
                        manifest=manifest,
                        path=Path(info.get("path", "")),
                        installed_at=datetime.fromisoformat(info.get("installed_at", datetime.now().isoformat())),
                        enabled=info.get("enabled", True),
                    )
            except Exception as e:
                logger.warning(f"Failed to load installed skills: {e}")
    
    def _save_installed(self) -> None:
        """Save installed skills to disk."""
        try:
            data = {
                skill_id: skill.to_dict()
                for skill_id, skill in self._installed_skills.items()
            }
            with open(self.installed_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save installed skills: {e}")
    
    async def search(
        self,
        query: str = "",
        tags: list[str] = None,
        limit: int = 20,
    ) -> list[SkillManifest]:
        """
        Search for skills.
        
        Args:
            query: Search query (matches name, description)
            tags: Filter by tags
            limit: Maximum results
            
        Returns:
            List of matching SkillManifest
        """
        results = []
        query_lower = query.lower()
        
        # Search built-in skills first
        for skill in BUILTIN_SKILLS:
            if query_lower in skill.name.lower() or query_lower in skill.description.lower():
                results.append(skill)
            elif tags and any(t in skill.tags for t in tags):
                results.append(skill)
            elif not query and not tags:
                results.append(skill)
        
        # Try remote registry
        try:
            remote_results = await self._search_remote(query, tags, limit)
            for skill in remote_results:
                if skill.id not in [r.id for r in results]:
                    results.append(skill)
        except Exception as e:
            logger.debug(f"Remote search unavailable: {e}")
        
        return results[:limit]
    
    async def _search_remote(
        self,
        query: str,
        tags: list[str] = None,
        limit: int = 20,
    ) -> list[SkillManifest]:
        """Search remote registry."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                params = {"q": query, "limit": limit}
                if tags:
                    params["tags"] = ",".join(tags)
                
                response = await client.get(
                    f"{self.registry_url}/skills/search",
                    params=params,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [SkillManifest.from_dict(s) for s in data.get("skills", [])]
        except Exception as e:
            logger.debug(f"Remote search failed: {e}")
        
        return []
    
    async def get_skill(self, skill_id: str) -> Optional[SkillManifest]:
        """
        Get skill manifest by ID.
        
        Args:
            skill_id: Skill ID
            
        Returns:
            SkillManifest or None
        """
        # Check built-in
        for skill in BUILTIN_SKILLS:
            if skill.id == skill_id:
                return skill
        
        # Check remote
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.registry_url}/skills/{skill_id}")
                if response.status_code == 200:
                    return SkillManifest.from_dict(response.json())
        except Exception:
            pass
        
        return None
    
    async def install(
        self,
        skill_id: str,
        force: bool = False,
    ) -> tuple[bool, str]:
        """
        Install a skill.
        
        Supports:
        - Built-in skill IDs
        - Remote registry skill IDs
        - GitHub URLs: https://github.com/owner/repo/...
        - GitHub shorthand: github:owner/repo/path
        - SkillsMP IDs: owner-repo-path-skill-md
        
        Args:
            skill_id: Skill ID, GitHub URL, or shorthand
            force: Force reinstall if exists
            
        Returns:
            (success, message) tuple
        """
        # Check if it's a GitHub URL or shorthand
        if (skill_id.startswith("http") and "github.com" in skill_id) or \
           skill_id.startswith("github:") or \
           ("-" in skill_id and not any(s.id == skill_id for s in BUILTIN_SKILLS)):
            # Try GitHub installation first
            owner, repo, path = self._parse_github_url(skill_id)
            if owner and repo:
                return await self.install_from_github(skill_id, force)
        
        # Check if already installed (for non-GitHub skills)
        if skill_id in self._installed_skills and not force:
            return False, f"Skill '{skill_id}' is already installed"
        
        # Get manifest from registry
        manifest = await self.get_skill(skill_id)
        if not manifest:
            return False, f"Skill '{skill_id}' not found. Try: github:owner/repo/path"
        
        # Create skill directory
        skill_path = self.skills_dir / skill_id
        skill_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Check if it's a built-in skill
            is_builtin = any(s.id == skill_id for s in BUILTIN_SKILLS)
            
            if is_builtin:
                # Create skill files from template
                await self._create_builtin_skill(skill_id, skill_path, manifest)
            else:
                # Download from repository
                success = await self._download_skill(manifest, skill_path)
                if not success:
                    return False, f"Failed to download skill '{skill_id}'"
            
            # Save manifest
            manifest_path = skill_path / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest.to_dict(), f, indent=2)
            
            # Register as installed
            self._installed_skills[skill_id] = InstalledSkill(
                manifest=manifest,
                path=skill_path,
                installed_at=datetime.now(),
                enabled=True,
            )
            self._save_installed()
            
            logger.info(f"Installed skill: {skill_id} v{manifest.version}")
            return True, f"Successfully installed '{manifest.name}' v{manifest.version}"
            
        except Exception as e:
            logger.error(f"Failed to install skill: {e}")
            # Cleanup on failure
            if skill_path.exists():
                shutil.rmtree(skill_path, ignore_errors=True)
            return False, f"Installation failed: {str(e)}"
    
    async def _create_builtin_skill(
        self,
        skill_id: str,
        path: Path,
        manifest: SkillManifest,
    ) -> None:
        """Create files for a built-in skill."""
        # Create SKILL.md
        skill_md = f"""# {manifest.name}

{manifest.description}

## Commands

{chr(10).join(f"- `{cmd}`" for cmd in manifest.commands)}

## Tags

{', '.join(f"`{t}`" for t in manifest.tags)}

## Usage

This is a built-in skill. Use the commands above to interact with it.

## Version

{manifest.version}
"""
        (path / "SKILL.md").write_text(skill_md)
        
        # Create config.json
        config = {
            "enabled": True,
            "commands": manifest.commands,
            "settings": {},
        }
        with open(path / "config.json", "w") as f:
            json.dump(config, f, indent=2)
    
    async def _download_skill(
        self,
        manifest: SkillManifest,
        path: Path,
    ) -> bool:
        """Download skill from repository."""
        if not manifest.repository:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # Try to download as tarball
                if "github.com" in manifest.repository:
                    # GitHub tarball URL
                    tarball_url = f"{manifest.repository}/archive/refs/heads/main.tar.gz"
                    response = await client.get(tarball_url, follow_redirects=True)
                    
                    if response.status_code == 200:
                        # Extract tarball
                        import tarfile
                        import io
                        
                        tar = tarfile.open(fileobj=io.BytesIO(response.content))
                        tar.extractall(path=path)
                        tar.close()
                        
                        # Move contents from subdirectory
                        subdir = list(path.iterdir())[0]
                        for item in subdir.iterdir():
                            shutil.move(str(item), str(path))
                        subdir.rmdir()
                        
                        return True
                
                # Try registry download endpoint
                response = await client.get(
                    f"{self.registry_url}/skills/{manifest.id}/download",
                    follow_redirects=True,
                )
                
                if response.status_code == 200:
                    # Extract content
                    import tarfile
                    import io
                    
                    tar = tarfile.open(fileobj=io.BytesIO(response.content))
                    tar.extractall(path=path)
                    tar.close()
                    return True
                    
        except Exception as e:
            logger.error(f"Download failed: {e}")
        
        return False
    
    async def install_from_github(
        self,
        github_url: str,
        force: bool = False,
    ) -> tuple[bool, str]:
        """
        Install a skill directly from GitHub URL or shorthand.
        
        Supports formats:
        - Full URL: https://github.com/owner/repo/blob/main/.claude/skills/name/SKILL.md
        - Shorthand: github:owner/repo/.claude/skills/name
        - SkillsMP format: owner-repo-path-skill-md
        
        Args:
            github_url: GitHub URL or shorthand
            force: Force reinstall if exists
            
        Returns:
            (success, message) tuple
        """
        try:
            # Parse the URL/shorthand
            owner, repo, skill_path = self._parse_github_url(github_url)
            if not owner or not repo:
                return False, f"Invalid GitHub URL format: {github_url}"
            
            # Generate skill ID
            skill_id = f"{owner}-{repo}-{skill_path.replace('/', '-')}".rstrip('-')
            
            # Check if already installed
            if skill_id in self._installed_skills and not force:
                return False, f"Skill '{skill_id}' is already installed"
            
            # Download SKILL.md from GitHub
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{skill_path}/SKILL.md"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(raw_url)
                
                if response.status_code != 200:
                    # Try master branch
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{skill_path}/SKILL.md"
                    response = await client.get(raw_url)
                
                if response.status_code != 200:
                    return False, f"Failed to fetch SKILL.md from GitHub (status: {response.status_code})"
                
                skill_content = response.text
            
            # Parse SKILL.md to extract metadata
            manifest = self._parse_skill_md(skill_content, skill_id, owner, repo, skill_path)
            
            # Create skill directory
            skill_dir = self.skills_dir / skill_id
            skill_dir.mkdir(parents=True, exist_ok=True)
            
            # Save SKILL.md
            (skill_dir / "SKILL.md").write_text(skill_content)
            
            # Try to download additional files (config.json, scripts, etc.)
            for extra_file in ["config.json", "marketplace.json", "index.js", "index.ts", "main.py"]:
                try:
                    extra_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{skill_path}/{extra_file}"
                    extra_resp = await httpx.AsyncClient().get(extra_url, timeout=10)
                    if extra_resp.status_code == 200:
                        (skill_dir / extra_file).write_text(extra_resp.text)
                except Exception:
                    pass
            
            # Save manifest
            with open(skill_dir / "manifest.json", "w") as f:
                json.dump(manifest.to_dict(), f, indent=2)
            
            # Register as installed
            self._installed_skills[skill_id] = InstalledSkill(
                manifest=manifest,
                path=skill_dir,
                installed_at=datetime.now(),
                enabled=True,
            )
            self._save_installed()
            
            logger.info(f"Installed skill from GitHub: {skill_id}")
            return True, f"Successfully installed '{manifest.name}' from GitHub"
            
        except Exception as e:
            logger.error(f"Failed to install from GitHub: {e}")
            return False, f"Installation failed: {str(e)}"
    
    def _parse_github_url(self, url: str) -> tuple[str, str, str]:
        """Parse GitHub URL into owner, repo, and path components."""
        import re
        
        # Handle shorthand format: github:owner/repo/path
        if url.startswith("github:"):
            parts = url[7:].split("/", 2)
            if len(parts) >= 2:
                owner = parts[0]
                repo = parts[1]
                path = parts[2] if len(parts) > 2 else ".claude/skills"
                return owner, repo, path
        
        # Handle SkillsMP format: owner-repo-...-skill-md
        if "-" in url and not url.startswith("http"):
            parts = url.replace("-skill-md", "").split("-")
            if len(parts) >= 2:
                owner = parts[0]
                repo = parts[1]
                # Reconstruct path from remaining parts
                path = "/".join(parts[2:]) if len(parts) > 2 else ".claude/skills"
                return owner, repo, path
        
        # Handle full GitHub URL
        patterns = [
            r"github\.com/([^/]+)/([^/]+)/(?:blob|tree)/[^/]+/(.+?)(?:/SKILL\.md)?$",
            r"github\.com/([^/]+)/([^/]+)/(.+?)(?:/SKILL\.md)?$",
            r"github\.com/([^/]+)/([^/]+)/?$",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                groups = match.groups()
                owner = groups[0]
                repo = groups[1]
                path = groups[2] if len(groups) > 2 and groups[2] else ".claude/skills"
                return owner, repo, path.rstrip("/")
        
        return "", "", ""
    
    def _parse_skill_md(
        self,
        content: str,
        skill_id: str,
        owner: str,
        repo: str,
        path: str,
    ) -> SkillManifest:
        """Parse SKILL.md content to extract metadata."""
        import re
        
        # Extract title (first # heading)
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        name = title_match.group(1) if title_match else skill_id
        
        # Extract description (first paragraph after title)
        desc_match = re.search(r"^#.+\n+(.+?)(?:\n\n|$)", content, re.MULTILINE)
        description = desc_match.group(1) if desc_match else f"Skill from {owner}/{repo}"
        
        # Extract commands (from ## Commands section or inline code)
        commands = []
        cmd_section = re.search(r"##\s*Commands?\s*\n([\s\S]*?)(?=\n##|$)", content, re.IGNORECASE)
        if cmd_section:
            commands = re.findall(r"`([^`]+)`", cmd_section.group(1))
        
        # Extract tags
        tags = []
        tag_section = re.search(r"##\s*Tags?\s*\n([\s\S]*?)(?=\n##|$)", content, re.IGNORECASE)
        if tag_section:
            tags = re.findall(r"`([^`]+)`", tag_section.group(1))
        
        return SkillManifest(
            id=skill_id,
            name=name.strip(),
            description=description.strip()[:200],
            version="1.0.0",
            author=owner,
            tags=tags[:10],
            commands=commands[:20],
            repository=f"https://github.com/{owner}/{repo}",
            homepage=f"https://github.com/{owner}/{repo}",
            license="MIT",
        )

    async def search_github(
        self,
        query: str,
        limit: int = 20,
    ) -> list[SkillManifest]:
        """
        Search for SKILL.md files on GitHub.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of SkillManifest from GitHub
        """
        results = []
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Search GitHub for SKILL.md files
                search_url = "https://api.github.com/search/code"
                params = {
                    "q": f"{query} filename:SKILL.md",
                    "per_page": min(limit, 30),
                }
                
                headers = {"Accept": "application/vnd.github.v3+json"}
                
                # Add GitHub token if available
                github_token = os.getenv("GITHUB_TOKEN")
                if github_token:
                    headers["Authorization"] = f"token {github_token}"
                
                response = await client.get(search_url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("items", [])[:limit]:
                        repo = item.get("repository", {})
                        owner = repo.get("owner", {}).get("login", "")
                        repo_name = repo.get("name", "")
                        path = item.get("path", "").replace("/SKILL.md", "")
                        
                        skill_id = f"{owner}-{repo_name}-{path.replace('/', '-')}"
                        
                        results.append(SkillManifest(
                            id=skill_id,
                            name=item.get("name", skill_id).replace(".md", ""),
                            description=f"Skill from {owner}/{repo_name}",
                            version="1.0.0",
                            author=owner,
                            repository=repo.get("html_url", ""),
                            homepage=item.get("html_url", ""),
                        ))
                elif response.status_code == 403:
                    logger.warning("GitHub API rate limit reached. Set GITHUB_TOKEN for higher limits.")
                    
        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
        
        return results

    async def uninstall(self, skill_id: str) -> tuple[bool, str]:
        """
        Uninstall a skill.
        
        Args:
            skill_id: Skill ID to uninstall
            
        Returns:
            (success, message) tuple
        """
        if skill_id not in self._installed_skills:
            return False, f"Skill '{skill_id}' is not installed"
        
        try:
            skill = self._installed_skills[skill_id]
            
            # Remove directory
            if skill.path.exists():
                shutil.rmtree(skill.path)
            
            # Remove from registry
            del self._installed_skills[skill_id]
            self._save_installed()
            
            logger.info(f"Uninstalled skill: {skill_id}")
            return True, f"Successfully uninstalled '{skill.manifest.name}'"
            
        except Exception as e:
            logger.error(f"Failed to uninstall skill: {e}")
            return False, f"Uninstallation failed: {str(e)}"
    
    async def update(self, skill_id: str) -> tuple[bool, str]:
        """
        Update a skill to latest version.
        
        Args:
            skill_id: Skill ID to update
            
        Returns:
            (success, message) tuple
        """
        if skill_id not in self._installed_skills:
            return False, f"Skill '{skill_id}' is not installed"
        
        current = self._installed_skills[skill_id]
        latest = await self.get_skill(skill_id)
        
        if not latest:
            return False, f"Could not find skill '{skill_id}' in registry"
        
        if latest.version == current.manifest.version:
            return True, f"Skill '{skill_id}' is already up to date (v{latest.version})"
        
        # Reinstall with force
        return await self.install(skill_id, force=True)
    
    def list_installed(self) -> list[InstalledSkill]:
        """List all installed skills."""
        return list(self._installed_skills.values())
    
    def get_installed(self, skill_id: str) -> Optional[InstalledSkill]:
        """Get an installed skill by ID."""
        return self._installed_skills.get(skill_id)
    
    def is_installed(self, skill_id: str) -> bool:
        """Check if a skill is installed."""
        return skill_id in self._installed_skills
    
    async def enable(self, skill_id: str) -> bool:
        """Enable an installed skill."""
        if skill_id not in self._installed_skills:
            return False
        
        self._installed_skills[skill_id].enabled = True
        self._save_installed()
        return True
    
    async def disable(self, skill_id: str) -> bool:
        """Disable an installed skill."""
        if skill_id not in self._installed_skills:
            return False
        
        self._installed_skills[skill_id].enabled = False
        self._save_installed()
        return True
    
    def list_builtin(self) -> list[SkillManifest]:
        """List all built-in skills."""
        return BUILTIN_SKILLS.copy()
    
    def get_stats(self) -> dict:
        """Get registry statistics."""
        installed = self.list_installed()
        enabled = [s for s in installed if s.enabled]
        
        return {
            "builtin_count": len(BUILTIN_SKILLS),
            "installed_count": len(installed),
            "enabled_count": len(enabled),
            "disabled_count": len(installed) - len(enabled),
            "registry_url": self.registry_url,
            "skills_dir": str(self.skills_dir),
        }


# Global instance
_skills_registry: Optional[SkillsRegistry] = None


def get_skills_registry() -> SkillsRegistry:
    """Get the global skills registry instance."""
    global _skills_registry
    
    if _skills_registry is None:
        _skills_registry = SkillsRegistry()
    
    return _skills_registry


__all__ = [
    "SkillsRegistry",
    "SkillManifest",
    "InstalledSkill",
    "get_skills_registry",
    "BUILTIN_SKILLS",
]
