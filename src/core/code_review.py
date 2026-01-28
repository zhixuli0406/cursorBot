"""
Code Review Agent for CursorBot

Automated code review with AI-powered analysis.

Features:
- Static analysis integration (pylint, eslint, etc.)
- AI-powered code quality assessment
- Security vulnerability detection
- Best practices suggestions
- Git diff analysis
- Pull request review

Usage:
    from src.core.code_review import get_code_reviewer, ReviewConfig
    
    reviewer = get_code_reviewer()
    
    # Review a file
    result = await reviewer.review_file("src/main.py")
    
    # Review a diff
    result = await reviewer.review_diff(diff_content)
    
    # Review a pull request (GitHub)
    result = await reviewer.review_pr("owner/repo", 123)
"""

import asyncio
import os
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, Union

from ..utils.logger import logger


# ============================================
# Review Types
# ============================================

class ReviewSeverity(Enum):
    """Severity levels for review findings."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReviewCategory(Enum):
    """Categories of review findings."""
    STYLE = "style"
    QUALITY = "quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    BEST_PRACTICE = "best_practice"
    BUG = "bug"


@dataclass
class ReviewFinding:
    """A single finding from code review."""
    message: str
    severity: ReviewSeverity
    category: ReviewCategory
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    rule_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion,
            "rule_id": self.rule_id,
        }


@dataclass
class ReviewResult:
    """Result of a code review."""
    success: bool
    findings: list[ReviewFinding] = field(default_factory=list)
    summary: str = ""
    score: float = 0.0  # 0-100
    
    # Metadata
    files_reviewed: int = 0
    lines_reviewed: int = 0
    duration_ms: int = 0
    reviewed_at: datetime = field(default_factory=datetime.now)
    
    # Statistics by severity
    info_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    critical_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "score": self.score,
            "files_reviewed": self.files_reviewed,
            "lines_reviewed": self.lines_reviewed,
            "duration_ms": self.duration_ms,
            "reviewed_at": self.reviewed_at.isoformat(),
            "statistics": {
                "info": self.info_count,
                "warning": self.warning_count,
                "error": self.error_count,
                "critical": self.critical_count,
            },
        }
    
    def add_finding(self, finding: ReviewFinding) -> None:
        """Add a finding and update statistics."""
        self.findings.append(finding)
        if finding.severity == ReviewSeverity.INFO:
            self.info_count += 1
        elif finding.severity == ReviewSeverity.WARNING:
            self.warning_count += 1
        elif finding.severity == ReviewSeverity.ERROR:
            self.error_count += 1
        elif finding.severity == ReviewSeverity.CRITICAL:
            self.critical_count += 1


@dataclass
class ReviewConfig:
    """Configuration for code review."""
    # Analysis options
    enable_static_analysis: bool = True
    enable_ai_review: bool = True
    enable_security_scan: bool = True
    
    # Severity thresholds
    min_severity: ReviewSeverity = ReviewSeverity.INFO
    fail_on_error: bool = True
    fail_on_critical: bool = True
    
    # AI options
    ai_model: str = ""  # Uses default if empty
    ai_temperature: float = 0.3
    max_tokens: int = 4000
    
    # Language-specific analyzers
    python_linter: str = "pylint"  # pylint, flake8, ruff
    js_linter: str = "eslint"
    
    # Ignore patterns
    ignore_patterns: list[str] = field(default_factory=lambda: [
        "*.min.js",
        "*.min.css",
        "node_modules/*",
        "venv/*",
        "__pycache__/*",
        "*.pyc",
        ".git/*",
    ])
    
    # Focus areas
    focus_categories: list[ReviewCategory] = field(default_factory=list)


# ============================================
# Static Analyzers
# ============================================

class StaticAnalyzer(ABC):
    """Base class for static code analyzers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Analyzer name."""
        pass
    
    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """File extensions this analyzer supports."""
        pass
    
    @abstractmethod
    async def analyze(self, file_path: str, content: str = None) -> list[ReviewFinding]:
        """Analyze a file and return findings."""
        pass
    
    def supports_file(self, file_path: str) -> bool:
        """Check if this analyzer supports the given file."""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions


class PylintAnalyzer(StaticAnalyzer):
    """Python linter using pylint."""
    
    @property
    def name(self) -> str:
        return "pylint"
    
    @property
    def supported_extensions(self) -> list[str]:
        return [".py"]
    
    async def analyze(self, file_path: str, content: str = None) -> list[ReviewFinding]:
        findings = []
        
        try:
            # Run pylint
            proc = await asyncio.create_subprocess_exec(
                "pylint",
                "--output-format=json",
                "--disable=C0114,C0115,C0116",  # Disable docstring warnings
                file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            
            if stdout:
                import json
                issues = json.loads(stdout.decode())
                
                for issue in issues:
                    severity = self._map_severity(issue.get("type", ""))
                    category = self._map_category(issue.get("symbol", ""))
                    
                    findings.append(ReviewFinding(
                        message=issue.get("message", ""),
                        severity=severity,
                        category=category,
                        file_path=file_path,
                        line_start=issue.get("line"),
                        code_snippet=issue.get("obj", ""),
                        rule_id=issue.get("symbol"),
                    ))
                    
        except FileNotFoundError:
            logger.debug("pylint not installed, skipping Python analysis")
        except Exception as e:
            logger.warning(f"Pylint analysis failed: {e}")
        
        return findings
    
    def _map_severity(self, pylint_type: str) -> ReviewSeverity:
        mapping = {
            "convention": ReviewSeverity.INFO,
            "refactor": ReviewSeverity.INFO,
            "warning": ReviewSeverity.WARNING,
            "error": ReviewSeverity.ERROR,
            "fatal": ReviewSeverity.CRITICAL,
        }
        return mapping.get(pylint_type, ReviewSeverity.INFO)
    
    def _map_category(self, symbol: str) -> ReviewCategory:
        if symbol.startswith("C"):
            return ReviewCategory.STYLE
        elif symbol.startswith("R"):
            return ReviewCategory.MAINTAINABILITY
        elif symbol.startswith("W"):
            return ReviewCategory.QUALITY
        elif symbol.startswith("E"):
            return ReviewCategory.BUG
        elif symbol.startswith("F"):
            return ReviewCategory.BUG
        return ReviewCategory.QUALITY


class RuffAnalyzer(StaticAnalyzer):
    """Fast Python linter using ruff."""
    
    @property
    def name(self) -> str:
        return "ruff"
    
    @property
    def supported_extensions(self) -> list[str]:
        return [".py"]
    
    async def analyze(self, file_path: str, content: str = None) -> list[ReviewFinding]:
        findings = []
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "ruff",
                "check",
                "--output-format=json",
                file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            if stdout:
                import json
                issues = json.loads(stdout.decode())
                
                for issue in issues:
                    findings.append(ReviewFinding(
                        message=issue.get("message", ""),
                        severity=ReviewSeverity.WARNING,
                        category=ReviewCategory.QUALITY,
                        file_path=issue.get("filename"),
                        line_start=issue.get("location", {}).get("row"),
                        rule_id=issue.get("code"),
                    ))
                    
        except FileNotFoundError:
            logger.debug("ruff not installed, skipping")
        except Exception as e:
            logger.warning(f"Ruff analysis failed: {e}")
        
        return findings


class ESLintAnalyzer(StaticAnalyzer):
    """JavaScript/TypeScript linter using eslint."""
    
    @property
    def name(self) -> str:
        return "eslint"
    
    @property
    def supported_extensions(self) -> list[str]:
        return [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]
    
    async def analyze(self, file_path: str, content: str = None) -> list[ReviewFinding]:
        findings = []
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "npx", "eslint",
                "--format=json",
                file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            
            if stdout:
                import json
                results = json.loads(stdout.decode())
                
                for result in results:
                    for msg in result.get("messages", []):
                        severity = ReviewSeverity.ERROR if msg.get("severity") == 2 else ReviewSeverity.WARNING
                        
                        findings.append(ReviewFinding(
                            message=msg.get("message", ""),
                            severity=severity,
                            category=ReviewCategory.QUALITY,
                            file_path=result.get("filePath"),
                            line_start=msg.get("line"),
                            line_end=msg.get("endLine"),
                            rule_id=msg.get("ruleId"),
                        ))
                        
        except FileNotFoundError:
            logger.debug("eslint not installed, skipping JavaScript analysis")
        except Exception as e:
            logger.warning(f"ESLint analysis failed: {e}")
        
        return findings


# ============================================
# AI Code Reviewer
# ============================================

class AICodeReviewer:
    """AI-powered code review using LLM."""
    
    def __init__(self, config: ReviewConfig = None):
        self.config = config or ReviewConfig()
    
    async def review(
        self,
        code: str,
        file_path: str = None,
        language: str = None,
        context: str = None,
    ) -> list[ReviewFinding]:
        """Review code using AI."""
        findings = []
        
        try:
            from .llm_providers import get_llm_manager
            
            llm = get_llm_manager()
            
            # Detect language if not provided
            if not language and file_path:
                language = self._detect_language(file_path)
            
            # Build review prompt
            prompt = self._build_review_prompt(code, language, context)
            
            # Get AI review
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.ai_temperature,
                max_tokens=self.config.max_tokens,
            )
            
            # Parse AI response
            findings = self._parse_ai_response(response, file_path)
            
        except Exception as e:
            logger.error(f"AI code review failed: {e}")
        
        return findings
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "React JSX",
            ".tsx": "React TSX",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".cpp": "C++",
            ".c": "C",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "Unknown")
    
    def _build_review_prompt(
        self,
        code: str,
        language: str = None,
        context: str = None,
    ) -> str:
        """Build the code review prompt."""
        lang_str = f"({language})" if language else ""
        
        prompt = f"""Please review the following code {lang_str} and provide detailed feedback.

Focus on:
1. **Bugs & Errors**: Potential bugs, logic errors, or runtime issues
2. **Security**: Security vulnerabilities (injection, XSS, etc.)
3. **Performance**: Performance issues or optimization opportunities
4. **Code Quality**: Readability, maintainability, best practices
5. **Suggestions**: Specific improvements with code examples

Format your response as a JSON array of findings:
```json
[
  {{
    "message": "Description of the issue",
    "severity": "info|warning|error|critical",
    "category": "bug|security|performance|quality|style|documentation",
    "line_start": 10,
    "line_end": 12,
    "suggestion": "Suggested fix or improvement"
  }}
]
```

"""
        if context:
            prompt += f"Context: {context}\n\n"
        
        prompt += f"Code to review:\n```\n{code}\n```"
        
        return prompt
    
    def _parse_ai_response(
        self,
        response: str,
        file_path: str = None,
    ) -> list[ReviewFinding]:
        """Parse AI response into findings."""
        findings = []
        
        try:
            # Extract JSON from response
            import json
            
            # Try to find JSON array in response
            json_match = re.search(r'\[[\s\S]*?\]', response)
            if json_match:
                items = json.loads(json_match.group())
                
                for item in items:
                    severity = ReviewSeverity(item.get("severity", "info"))
                    
                    # Map category
                    cat_str = item.get("category", "quality").lower()
                    category_map = {
                        "bug": ReviewCategory.BUG,
                        "security": ReviewCategory.SECURITY,
                        "performance": ReviewCategory.PERFORMANCE,
                        "quality": ReviewCategory.QUALITY,
                        "style": ReviewCategory.STYLE,
                        "documentation": ReviewCategory.DOCUMENTATION,
                    }
                    category = category_map.get(cat_str, ReviewCategory.QUALITY)
                    
                    findings.append(ReviewFinding(
                        message=item.get("message", ""),
                        severity=severity,
                        category=category,
                        file_path=file_path,
                        line_start=item.get("line_start"),
                        line_end=item.get("line_end"),
                        suggestion=item.get("suggestion"),
                    ))
                    
        except Exception as e:
            logger.warning(f"Failed to parse AI response: {e}")
            # Create a general finding from the response
            findings.append(ReviewFinding(
                message=response[:500],
                severity=ReviewSeverity.INFO,
                category=ReviewCategory.QUALITY,
                file_path=file_path,
            ))
        
        return findings


# ============================================
# Security Scanner
# ============================================

class SecurityScanner:
    """Security vulnerability scanner."""
    
    SECURITY_PATTERNS = {
        "python": [
            (r"eval\s*\(", "Use of eval() - potential code injection", ReviewSeverity.CRITICAL),
            (r"exec\s*\(", "Use of exec() - potential code injection", ReviewSeverity.CRITICAL),
            (r"subprocess\..*shell\s*=\s*True", "Shell=True in subprocess - command injection risk", ReviewSeverity.ERROR),
            (r"pickle\.load", "Unsafe pickle deserialization", ReviewSeverity.ERROR),
            (r"yaml\.load\([^,]+\)", "Unsafe YAML load without Loader", ReviewSeverity.ERROR),
            (r"__import__\s*\(", "Dynamic import - potential code injection", ReviewSeverity.WARNING),
            (r"os\.system\s*\(", "Use of os.system() - prefer subprocess", ReviewSeverity.WARNING),
            (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password detected", ReviewSeverity.CRITICAL),
            (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key detected", ReviewSeverity.CRITICAL),
            (r"secret\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret detected", ReviewSeverity.CRITICAL),
        ],
        "javascript": [
            (r"eval\s*\(", "Use of eval() - potential code injection", ReviewSeverity.CRITICAL),
            (r"innerHTML\s*=", "Direct innerHTML assignment - XSS risk", ReviewSeverity.ERROR),
            (r"document\.write\s*\(", "Use of document.write() - XSS risk", ReviewSeverity.ERROR),
            (r"new\s+Function\s*\(", "Dynamic function creation - code injection risk", ReviewSeverity.ERROR),
            (r"\.outerHTML\s*=", "Direct outerHTML assignment - XSS risk", ReviewSeverity.WARNING),
            (r"localStorage\.setItem.*password", "Storing password in localStorage", ReviewSeverity.ERROR),
            (r"password\s*[:=]\s*['\"][^'\"]+['\"]", "Hardcoded password detected", ReviewSeverity.CRITICAL),
            (r"api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]", "Hardcoded API key detected", ReviewSeverity.CRITICAL),
        ],
    }
    
    async def scan(self, code: str, language: str = None) -> list[ReviewFinding]:
        """Scan code for security issues."""
        findings = []
        
        # Normalize language
        lang = (language or "").lower()
        if lang in ("python", "py"):
            patterns = self.SECURITY_PATTERNS.get("python", [])
        elif lang in ("javascript", "js", "typescript", "ts"):
            patterns = self.SECURITY_PATTERNS.get("javascript", [])
        else:
            # Check all patterns
            patterns = []
            for p in self.SECURITY_PATTERNS.values():
                patterns.extend(p)
        
        lines = code.split("\n")
        
        for pattern, message, severity in patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(ReviewFinding(
                        message=message,
                        severity=severity,
                        category=ReviewCategory.SECURITY,
                        line_start=i,
                        code_snippet=line.strip(),
                    ))
        
        return findings


# ============================================
# Code Review Manager
# ============================================

class CodeReviewManager:
    """Main code review manager."""
    
    def __init__(self, config: ReviewConfig = None):
        self.config = config or ReviewConfig()
        
        # Initialize analyzers
        self._analyzers: list[StaticAnalyzer] = [
            PylintAnalyzer(),
            RuffAnalyzer(),
            ESLintAnalyzer(),
        ]
        
        self._ai_reviewer = AICodeReviewer(self.config)
        self._security_scanner = SecurityScanner()
    
    async def review_file(
        self,
        file_path: str,
        config: ReviewConfig = None,
    ) -> ReviewResult:
        """Review a single file."""
        config = config or self.config
        start_time = datetime.now()
        result = ReviewResult(success=True, files_reviewed=1)
        
        try:
            # Check if file exists
            path = Path(file_path)
            if not path.exists():
                result.success = False
                result.summary = f"File not found: {file_path}"
                return result
            
            # Check ignore patterns
            if self._should_ignore(file_path, config):
                result.summary = f"File ignored: {file_path}"
                return result
            
            # Read file content
            content = path.read_text(encoding="utf-8", errors="ignore")
            result.lines_reviewed = len(content.split("\n"))
            
            # Run static analysis
            if config.enable_static_analysis:
                for analyzer in self._analyzers:
                    if analyzer.supports_file(file_path):
                        findings = await analyzer.analyze(file_path, content)
                        for f in findings:
                            f.file_path = file_path
                            result.add_finding(f)
            
            # Run security scan
            if config.enable_security_scan:
                lang = self._detect_language(file_path)
                security_findings = await self._security_scanner.scan(content, lang)
                for f in security_findings:
                    f.file_path = file_path
                    result.add_finding(f)
            
            # Run AI review
            if config.enable_ai_review:
                ai_findings = await self._ai_reviewer.review(
                    content, file_path,
                    language=self._detect_language(file_path),
                )
                for f in ai_findings:
                    result.add_finding(f)
            
            # Calculate score
            result.score = self._calculate_score(result)
            
            # Generate summary
            result.summary = self._generate_summary(result)
            
        except Exception as e:
            logger.error(f"Review failed for {file_path}: {e}")
            result.success = False
            result.summary = f"Review failed: {str(e)}"
        
        result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return result
    
    async def review_files(
        self,
        file_paths: list[str],
        config: ReviewConfig = None,
    ) -> ReviewResult:
        """Review multiple files."""
        config = config or self.config
        start_time = datetime.now()
        
        combined_result = ReviewResult(success=True)
        
        for file_path in file_paths:
            file_result = await self.review_file(file_path, config)
            
            # Merge results
            combined_result.files_reviewed += file_result.files_reviewed
            combined_result.lines_reviewed += file_result.lines_reviewed
            combined_result.findings.extend(file_result.findings)
            combined_result.info_count += file_result.info_count
            combined_result.warning_count += file_result.warning_count
            combined_result.error_count += file_result.error_count
            combined_result.critical_count += file_result.critical_count
            
            if not file_result.success:
                combined_result.success = False
        
        combined_result.score = self._calculate_score(combined_result)
        combined_result.summary = self._generate_summary(combined_result)
        combined_result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return combined_result
    
    async def review_directory(
        self,
        directory: str,
        config: ReviewConfig = None,
        recursive: bool = True,
    ) -> ReviewResult:
        """Review all files in a directory."""
        config = config or self.config
        
        file_paths = []
        path = Path(directory)
        
        if recursive:
            for file_path in path.rglob("*"):
                if file_path.is_file() and not self._should_ignore(str(file_path), config):
                    file_paths.append(str(file_path))
        else:
            for file_path in path.glob("*"):
                if file_path.is_file() and not self._should_ignore(str(file_path), config):
                    file_paths.append(str(file_path))
        
        return await self.review_files(file_paths, config)
    
    async def review_diff(
        self,
        diff_content: str,
        config: ReviewConfig = None,
    ) -> ReviewResult:
        """Review a git diff."""
        config = config or self.config
        start_time = datetime.now()
        result = ReviewResult(success=True)
        
        try:
            # Parse diff to extract changed files and code
            changed_files = self._parse_diff(diff_content)
            
            for file_path, additions, deletions in changed_files:
                # Review only additions (new/changed code)
                if additions:
                    code = "\n".join(additions)
                    
                    # Security scan
                    if config.enable_security_scan:
                        lang = self._detect_language(file_path)
                        security_findings = await self._security_scanner.scan(code, lang)
                        for f in security_findings:
                            f.file_path = file_path
                            result.add_finding(f)
                    
                    # AI review
                    if config.enable_ai_review:
                        ai_findings = await self._ai_reviewer.review(
                            code, file_path,
                            context="This is new/changed code from a diff",
                        )
                        for f in ai_findings:
                            result.add_finding(f)
                
                result.files_reviewed += 1
                result.lines_reviewed += len(additions)
            
            result.score = self._calculate_score(result)
            result.summary = self._generate_summary(result)
            
        except Exception as e:
            logger.error(f"Diff review failed: {e}")
            result.success = False
            result.summary = f"Review failed: {str(e)}"
        
        result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return result
    
    async def review_pr(
        self,
        repo: str,
        pr_number: int,
        config: ReviewConfig = None,
    ) -> ReviewResult:
        """Review a GitHub pull request."""
        config = config or self.config
        
        try:
            # Fetch PR diff from GitHub
            import aiohttp
            
            # Try with token if available
            headers = {}
            token = os.getenv("GITHUB_TOKEN")
            if token:
                headers["Authorization"] = f"token {token}"
            headers["Accept"] = "application/vnd.github.v3.diff"
            
            url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        return ReviewResult(
                            success=False,
                            summary=f"Failed to fetch PR: HTTP {resp.status}",
                        )
                    diff_content = await resp.text()
            
            result = await self.review_diff(diff_content, config)
            result.summary = f"PR #{pr_number} Review: {result.summary}"
            
            return result
            
        except Exception as e:
            logger.error(f"PR review failed: {e}")
            return ReviewResult(
                success=False,
                summary=f"PR review failed: {str(e)}",
            )
    
    def _should_ignore(self, file_path: str, config: ReviewConfig) -> bool:
        """Check if file should be ignored."""
        import fnmatch
        
        for pattern in config.ignore_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True
            if fnmatch.fnmatch(Path(file_path).name, pattern):
                return True
        
        return False
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "c",
            ".rb": "ruby",
            ".php": "php",
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "")
    
    def _parse_diff(self, diff_content: str) -> list[tuple[str, list[str], list[str]]]:
        """Parse git diff content."""
        files = []
        current_file = None
        additions = []
        deletions = []
        
        for line in diff_content.split("\n"):
            if line.startswith("diff --git"):
                if current_file:
                    files.append((current_file, additions, deletions))
                # Extract file path
                parts = line.split(" b/")
                current_file = parts[-1] if len(parts) > 1 else ""
                additions = []
                deletions = []
            elif line.startswith("+") and not line.startswith("+++"):
                additions.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                deletions.append(line[1:])
        
        if current_file:
            files.append((current_file, additions, deletions))
        
        return files
    
    def _calculate_score(self, result: ReviewResult) -> float:
        """Calculate review score (0-100)."""
        if result.lines_reviewed == 0:
            return 100.0
        
        # Deductions per issue type
        deductions = (
            result.info_count * 0.5 +
            result.warning_count * 2 +
            result.error_count * 5 +
            result.critical_count * 15
        )
        
        # Normalize by lines reviewed
        normalized_deductions = (deductions / result.lines_reviewed) * 100
        
        score = max(0, 100 - normalized_deductions)
        return round(score, 1)
    
    def _generate_summary(self, result: ReviewResult) -> str:
        """Generate review summary."""
        total = len(result.findings)
        
        if total == 0:
            return f"No issues found. Score: {result.score}/100"
        
        summary_parts = []
        
        if result.critical_count > 0:
            summary_parts.append(f"{result.critical_count} critical")
        if result.error_count > 0:
            summary_parts.append(f"{result.error_count} errors")
        if result.warning_count > 0:
            summary_parts.append(f"{result.warning_count} warnings")
        if result.info_count > 0:
            summary_parts.append(f"{result.info_count} info")
        
        return f"Found {total} issues ({', '.join(summary_parts)}). Score: {result.score}/100"
    
    def format_findings(
        self,
        result: ReviewResult,
        format: str = "text",
    ) -> str:
        """Format findings for display."""
        if format == "json":
            import json
            return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
        
        if format == "markdown":
            return self._format_markdown(result)
        
        # Default text format
        return self._format_text(result)
    
    def _format_text(self, result: ReviewResult) -> str:
        """Format as plain text."""
        lines = [
            f"Code Review Result",
            f"==================",
            f"Files reviewed: {result.files_reviewed}",
            f"Lines reviewed: {result.lines_reviewed}",
            f"Score: {result.score}/100",
            f"Duration: {result.duration_ms}ms",
            f"",
            f"Summary: {result.summary}",
            f"",
        ]
        
        if result.findings:
            lines.append("Findings:")
            lines.append("---------")
            
            for i, f in enumerate(result.findings, 1):
                severity_icon = {
                    ReviewSeverity.INFO: "ℹ️",
                    ReviewSeverity.WARNING: "⚠️",
                    ReviewSeverity.ERROR: "❌",
                    ReviewSeverity.CRITICAL: "🚨",
                }.get(f.severity, "•")
                
                lines.append(f"\n{i}. {severity_icon} [{f.severity.value.upper()}] {f.message}")
                if f.file_path:
                    loc = f"   File: {f.file_path}"
                    if f.line_start:
                        loc += f":{f.line_start}"
                    lines.append(loc)
                if f.suggestion:
                    lines.append(f"   Suggestion: {f.suggestion}")
        
        return "\n".join(lines)
    
    def _format_markdown(self, result: ReviewResult) -> str:
        """Format as Markdown."""
        lines = [
            "# Code Review Result",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Files reviewed | {result.files_reviewed} |",
            f"| Lines reviewed | {result.lines_reviewed} |",
            f"| Score | {result.score}/100 |",
            f"| Duration | {result.duration_ms}ms |",
            "",
            f"**Summary:** {result.summary}",
            "",
        ]
        
        if result.findings:
            lines.append("## Findings")
            lines.append("")
            
            # Group by severity
            by_severity = {}
            for f in result.findings:
                sev = f.severity.value
                if sev not in by_severity:
                    by_severity[sev] = []
                by_severity[sev].append(f)
            
            severity_order = ["critical", "error", "warning", "info"]
            
            for sev in severity_order:
                if sev in by_severity:
                    emoji = {"critical": "🚨", "error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(sev, "")
                    lines.append(f"### {emoji} {sev.capitalize()}")
                    lines.append("")
                    
                    for f in by_severity[sev]:
                        lines.append(f"- **{f.message}**")
                        if f.file_path:
                            loc = f.file_path
                            if f.line_start:
                                loc += f":{f.line_start}"
                            lines.append(f"  - Location: `{loc}`")
                        if f.category:
                            lines.append(f"  - Category: {f.category.value}")
                        if f.suggestion:
                            lines.append(f"  - Suggestion: {f.suggestion}")
                        lines.append("")
        
        return "\n".join(lines)


# ============================================
# Global Instance
# ============================================

_code_reviewer: Optional[CodeReviewManager] = None


def get_code_reviewer(config: ReviewConfig = None) -> CodeReviewManager:
    """Get the global code reviewer instance."""
    global _code_reviewer
    
    if _code_reviewer is None:
        _code_reviewer = CodeReviewManager(config)
        logger.info("Code reviewer initialized")
    
    return _code_reviewer


def reset_code_reviewer() -> None:
    """Reset the code reviewer instance."""
    global _code_reviewer
    _code_reviewer = None


__all__ = [
    # Types
    "ReviewSeverity",
    "ReviewCategory",
    "ReviewFinding",
    "ReviewResult",
    "ReviewConfig",
    # Analyzers
    "StaticAnalyzer",
    "PylintAnalyzer",
    "RuffAnalyzer",
    "ESLintAnalyzer",
    # AI Reviewer
    "AICodeReviewer",
    # Security
    "SecurityScanner",
    # Manager
    "CodeReviewManager",
    "get_code_reviewer",
    "reset_code_reviewer",
]
