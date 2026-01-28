#!/usr/bin/env python3
"""
Security Audit Script for CursorBot

Performs automated security checks:
- Dependency vulnerability scanning
- Code security patterns
- Secrets detection
- Configuration validation

Usage:
    python scripts/security_audit.py [--full] [--fix]

Options:
    --full  Run full audit including slow checks
    --fix   Attempt to auto-fix issues
"""

import os
import sys
import re
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional


class Severity(Enum):
    """Security issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityIssue:
    """Represents a security issue."""
    severity: Severity
    category: str
    title: str
    description: str
    file_path: str = ""
    line_number: int = 0
    recommendation: str = ""
    
    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "recommendation": self.recommendation,
        }


@dataclass
class AuditReport:
    """Security audit report."""
    timestamp: datetime = field(default_factory=datetime.now)
    issues: list[SecurityIssue] = field(default_factory=list)
    passed_checks: list[str] = field(default_factory=list)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)
    
    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.HIGH)
    
    @property
    def medium_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.MEDIUM)
    
    @property
    def low_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.LOW)
    
    @property
    def total_issues(self) -> int:
        return len(self.issues)
    
    def add_issue(self, issue: SecurityIssue):
        self.issues.append(issue)
    
    def add_passed(self, check_name: str):
        self.passed_checks.append(check_name)
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total_issues": self.total_issues,
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "passed_checks": len(self.passed_checks),
            },
            "issues": [i.to_dict() for i in self.issues],
            "passed_checks": self.passed_checks,
        }
    
    def print_summary(self):
        """Print formatted summary."""
        print("\n" + "=" * 60)
        print("SECURITY AUDIT REPORT")
        print("=" * 60)
        print(f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print("SUMMARY")
        print("-" * 40)
        print(f"  Critical: {self.critical_count}")
        print(f"  High:     {self.high_count}")
        print(f"  Medium:   {self.medium_count}")
        print(f"  Low:      {self.low_count}")
        print(f"  Total:    {self.total_issues}")
        print(f"  Passed:   {len(self.passed_checks)}")
        print()
        
        if self.issues:
            print("ISSUES")
            print("-" * 40)
            for issue in sorted(self.issues, key=lambda x: x.severity.value):
                severity_icon = {
                    Severity.CRITICAL: "🔴",
                    Severity.HIGH: "🟠",
                    Severity.MEDIUM: "🟡",
                    Severity.LOW: "🟢",
                    Severity.INFO: "⚪",
                }.get(issue.severity, "⚪")
                
                print(f"\n{severity_icon} [{issue.severity.value.upper()}] {issue.title}")
                print(f"   Category: {issue.category}")
                if issue.file_path:
                    print(f"   File: {issue.file_path}:{issue.line_number}")
                print(f"   {issue.description}")
                if issue.recommendation:
                    print(f"   Fix: {issue.recommendation}")
        
        print("\n" + "=" * 60)
        
        if self.critical_count > 0:
            print("⚠️  CRITICAL ISSUES FOUND - Immediate action required!")
        elif self.high_count > 0:
            print("⚠️  HIGH severity issues found - Action recommended")
        elif self.total_issues == 0:
            print("✅ No security issues found!")
        else:
            print("ℹ️  Some issues found - Review recommended")


class SecurityAuditor:
    """Main security auditor class."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.report = AuditReport()
    
    def run_full_audit(self) -> AuditReport:
        """Run complete security audit."""
        print("Starting security audit...")
        
        # 1. Check for secrets in code
        self._check_secrets()
        
        # 2. Check for dangerous patterns
        self._check_dangerous_patterns()
        
        # 3. Check dependencies
        self._check_dependencies()
        
        # 4. Check configuration
        self._check_configuration()
        
        # 5. Check file permissions
        self._check_file_permissions()
        
        # 6. Check for common vulnerabilities
        self._check_common_vulnerabilities()
        
        return self.report
    
    def _check_secrets(self):
        """Check for hardcoded secrets."""
        print("  Checking for hardcoded secrets...")
        
        secret_patterns = [
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "API key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Secret"),
            (r'password\s*=\s*["\'][^"\']+["\']', "Password"),
            (r'token\s*=\s*["\'][^"\']+["\']', "Token"),
            (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API key"),
            (r'sk-ant-[a-zA-Z0-9]{20,}', "Anthropic API key"),
            (r'ghp_[a-zA-Z0-9]{36}', "GitHub token"),
            (r'xoxb-[0-9]{11}-[0-9]{11}-[a-zA-Z0-9]{24}', "Slack bot token"),
        ]
        
        # Files to check
        py_files = list(self.project_root.glob("src/**/*.py"))
        
        found_secrets = False
        for file_path in py_files:
            try:
                content = file_path.read_text()
                for pattern, secret_type in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Skip if it's getting from environment
                        line_start = content.rfind("\n", 0, match.start()) + 1
                        line = content[line_start:content.find("\n", match.end())]
                        
                        if "os.getenv" in line or "os.environ" in line:
                            continue
                        if "settings." in line:
                            continue
                        if "# " in line and match.start() > line.find("#"):
                            continue
                        
                        line_num = content[:match.start()].count("\n") + 1
                        
                        self.report.add_issue(SecurityIssue(
                            severity=Severity.CRITICAL,
                            category="secrets",
                            title=f"Potential hardcoded {secret_type}",
                            description=f"Found potential hardcoded secret in code",
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            recommendation="Move secrets to environment variables",
                        ))
                        found_secrets = True
                        
            except Exception as e:
                print(f"    Warning: Could not check {file_path}: {e}")
        
        if not found_secrets:
            self.report.add_passed("No hardcoded secrets found")
    
    def _check_dangerous_patterns(self):
        """Check for dangerous code patterns."""
        print("  Checking for dangerous patterns...")
        
        patterns = [
            (r'\beval\s*\(', Severity.CRITICAL, "eval() usage", "eval() can execute arbitrary code"),
            (r'\bexec\s*\(', Severity.CRITICAL, "exec() usage", "exec() can execute arbitrary code"),
            (r'subprocess\..*shell\s*=\s*True', Severity.HIGH, "Shell injection risk", "shell=True enables command injection"),
            (r'pickle\.loads?\(', Severity.HIGH, "Pickle deserialization", "Pickle can execute arbitrary code"),
            (r'yaml\.load\s*\([^)]*\)', Severity.MEDIUM, "Unsafe YAML load", "Use yaml.safe_load() instead"),
            (r'__import__\s*\(', Severity.MEDIUM, "Dynamic import", "Dynamic imports can be dangerous"),
            (r'os\.system\s*\(', Severity.MEDIUM, "os.system() usage", "Prefer subprocess with shell=False"),
        ]
        
        py_files = list(self.project_root.glob("src/**/*.py"))
        
        for file_path in py_files:
            try:
                content = file_path.read_text()
                
                for pattern, severity, title, description in patterns:
                    for match in re.finditer(pattern, content):
                        line_num = content[:match.start()].count("\n") + 1
                        
                        # Get context line
                        line_start = content.rfind("\n", 0, match.start()) + 1
                        line_end = content.find("\n", match.end())
                        line = content[line_start:line_end].strip()
                        
                        # Skip if in comment
                        if line.strip().startswith("#"):
                            continue
                        
                        self.report.add_issue(SecurityIssue(
                            severity=severity,
                            category="code_pattern",
                            title=title,
                            description=description,
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                        ))
                        
            except Exception as e:
                print(f"    Warning: Could not check {file_path}: {e}")
        
        if not any(i.category == "code_pattern" for i in self.report.issues):
            self.report.add_passed("No dangerous code patterns found")
    
    def _check_dependencies(self):
        """Check for vulnerable dependencies."""
        print("  Checking dependencies...")
        
        # Try pip-audit if available
        try:
            result = subprocess.run(
                ["pip-audit", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_root,
            )
            
            if result.returncode == 0:
                try:
                    vulns = json.loads(result.stdout)
                    for vuln in vulns.get("dependencies", []):
                        for v in vuln.get("vulns", []):
                            self.report.add_issue(SecurityIssue(
                                severity=Severity.HIGH,
                                category="dependency",
                                title=f"Vulnerable package: {vuln.get('name')}",
                                description=f"{v.get('id')}: {v.get('description', 'Unknown vulnerability')}",
                                recommendation=f"Upgrade to version {v.get('fix_versions', ['unknown'])}",
                            ))
                except json.JSONDecodeError:
                    pass
            
            if not any(i.category == "dependency" for i in self.report.issues):
                self.report.add_passed("No known vulnerable dependencies")
                
        except FileNotFoundError:
            print("    Warning: pip-audit not installed, skipping dependency check")
            print("    Install with: pip install pip-audit")
        except subprocess.TimeoutExpired:
            print("    Warning: Dependency check timed out")
    
    def _check_configuration(self):
        """Check configuration security."""
        print("  Checking configuration...")
        
        env_example = self.project_root / "env.example"
        
        if env_example.exists():
            content = env_example.read_text()
            
            # Check for default values that should not be defaults
            if re.search(r'DEBUG\s*=\s*true', content, re.IGNORECASE):
                self.report.add_issue(SecurityIssue(
                    severity=Severity.MEDIUM,
                    category="config",
                    title="Debug mode enabled by default",
                    description="DEBUG=true should not be the default",
                    file_path="env.example",
                    recommendation="Set DEBUG=false as default",
                ))
            
            # Check for example secrets that look real
            if re.search(r'sk-[a-zA-Z0-9]{20,}', content):
                self.report.add_issue(SecurityIssue(
                    severity=Severity.HIGH,
                    category="config",
                    title="Real API key in example config",
                    description="env.example contains what appears to be a real API key",
                    file_path="env.example",
                    recommendation="Use placeholder values in env.example",
                ))
        
        # Check .env is in .gitignore
        gitignore = self.project_root / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text()
            if ".env" not in content:
                self.report.add_issue(SecurityIssue(
                    severity=Severity.HIGH,
                    category="config",
                    title=".env not in .gitignore",
                    description="Environment file may be committed to git",
                    file_path=".gitignore",
                    recommendation="Add .env to .gitignore",
                ))
            else:
                self.report.add_passed(".env is in .gitignore")
    
    def _check_file_permissions(self):
        """Check for insecure file permissions."""
        print("  Checking file permissions...")
        
        sensitive_files = [
            ".env",
            "credentials.json",
            "service_account.json",
        ]
        
        for filename in sensitive_files:
            file_path = self.project_root / filename
            if file_path.exists():
                try:
                    mode = oct(file_path.stat().st_mode)[-3:]
                    if int(mode[2]) > 0:  # World readable
                        self.report.add_issue(SecurityIssue(
                            severity=Severity.MEDIUM,
                            category="permissions",
                            title=f"Sensitive file world-readable: {filename}",
                            description=f"File {filename} has permissions {mode}",
                            file_path=filename,
                            recommendation="Set permissions to 600 (chmod 600)",
                        ))
                except Exception:
                    pass
        
        if not any(i.category == "permissions" for i in self.report.issues):
            self.report.add_passed("File permissions are secure")
    
    def _check_common_vulnerabilities(self):
        """Check for common web vulnerabilities."""
        print("  Checking for common vulnerabilities...")
        
        py_files = list(self.project_root.glob("src/**/*.py"))
        
        # SQL Injection patterns
        sql_patterns = [
            r'execute\s*\(\s*[f"\'].*\{.*\}',  # f-string in execute
            r'execute\s*\(\s*["\'].*%s.*["\'].*%',  # String formatting
            r'\.format\s*\(.*\).*execute',  # .format() near execute
        ]
        
        for file_path in py_files:
            try:
                content = file_path.read_text()
                
                for pattern in sql_patterns:
                    for match in re.finditer(pattern, content):
                        line_num = content[:match.start()].count("\n") + 1
                        
                        self.report.add_issue(SecurityIssue(
                            severity=Severity.HIGH,
                            category="sql_injection",
                            title="Potential SQL injection",
                            description="Query appears to use string formatting instead of parameters",
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            recommendation="Use parameterized queries",
                        ))
                        
            except Exception:
                pass
        
        if not any(i.category == "sql_injection" for i in self.report.issues):
            self.report.add_passed("No SQL injection vulnerabilities found")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CursorBot Security Audit")
    parser.add_argument("--full", action="store_true", help="Run full audit")
    parser.add_argument("--fix", action="store_true", help="Attempt auto-fix")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", type=str, help="Output file path")
    
    args = parser.parse_args()
    
    # Find project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    
    # Run audit
    auditor = SecurityAuditor(project_root)
    report = auditor.run_full_audit()
    
    # Output results
    if args.json:
        output = json.dumps(report.to_dict(), indent=2)
        if args.output:
            Path(args.output).write_text(output)
        else:
            print(output)
    else:
        report.print_summary()
        
        if args.output:
            Path(args.output).write_text(json.dumps(report.to_dict(), indent=2))
            print(f"\nReport saved to: {args.output}")
    
    # Exit code based on severity
    if report.critical_count > 0:
        sys.exit(2)
    elif report.high_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
