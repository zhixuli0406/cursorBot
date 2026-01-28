# Contributing to CursorBot

First off, thank you for considering contributing to CursorBot! It's people like you that make CursorBot such a great tool.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Prerequisites

- Python 3.10 - 3.12 (3.13+ not supported)
- Git
- Docker (optional, for containerized development)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/cursorBot.git
   cd cursorBot
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/original-owner/cursorBot.git
   ```

## Development Setup

### Option 1: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Install pre-commit hooks
pre-commit install

# Copy environment file
cp env.example .env
# Edit .env with your configuration
```

### Option 2: Docker Development

```bash
# Build and start development container
docker compose -f docker-compose.dev.yml up -d

# Attach to container
docker exec -it cursorbot-dev bash
```

### Running the Application

```bash
# Local
python -m src.main

# Or use the start script
./start.sh  # Linux/macOS
start.bat   # Windows
```

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/` - New features (e.g., `feature/voice-commands`)
- `fix/` - Bug fixes (e.g., `fix/memory-leak`)
- `docs/` - Documentation (e.g., `docs/api-reference`)
- `refactor/` - Code refactoring (e.g., `refactor/session-manager`)
- `test/` - Test additions (e.g., `test/llm-providers`)

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style (formatting, semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(telegram): add voice message transcription

fix(session): resolve memory leak in long sessions

docs(readme): update installation instructions
```

## Coding Standards

### Python Style

We follow [PEP 8](https://pep8.org/) with some modifications:

- Line length: 100 characters (120 max)
- Use type hints for function parameters and return values
- Use docstrings for all public functions and classes

```python
async def process_message(
    message: str,
    user_id: str,
    context: Optional[dict] = None,
) -> ProcessResult:
    """
    Process an incoming message.
    
    Args:
        message: The message content
        user_id: Unique identifier for the user
        context: Optional context dictionary
        
    Returns:
        ProcessResult with status and response
        
    Raises:
        ValidationError: If message is invalid
    """
    ...
```

### Project Structure

```
cursorBot/
├── src/
│   ├── bot/          # Bot handlers (Telegram)
│   ├── channels/     # Platform channels
│   ├── cli/          # CLI tools
│   ├── core/         # Core functionality
│   ├── cursor/       # Cursor CLI integration
│   ├── platforms/    # Platform-specific code
│   ├── server/       # API server
│   ├── utils/        # Utilities
│   └── web/          # Web interfaces
├── skills/           # Custom skills
├── tests/            # Test files
├── docs/             # Documentation
└── data/             # Runtime data (gitignored)
```

### Import Order

```python
# Standard library
import os
import sys
from typing import Optional, List

# Third-party packages
import aiohttp
from pydantic import BaseModel

# Local imports
from ..utils.logger import logger
from ..core.memory import get_memory_manager
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_session.py

# Run tests matching pattern
pytest -k "test_memory"
```

### Writing Tests

- Place tests in the `tests/` directory
- Mirror the source structure (e.g., `src/core/session.py` → `tests/test_session.py`)
- Use descriptive test names
- Include both positive and negative test cases

```python
import pytest
from src.core.session import SessionManager

class TestSessionManager:
    """Tests for SessionManager."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh SessionManager for each test."""
        return SessionManager()
    
    def test_create_session(self, manager):
        """Test creating a new session."""
        session = manager.create_session("user123")
        assert session is not None
        assert session.user_id == "user123"
    
    def test_create_session_duplicate(self, manager):
        """Test creating duplicate session raises error."""
        manager.create_session("user123")
        with pytest.raises(SessionExistsError):
            manager.create_session("user123")
```

### Test Coverage

We aim for >80% code coverage on core modules. New features should include tests.

## Pull Request Process

### Before Submitting

1. **Update your branch** with the latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run the full test suite**:
   ```bash
   pytest
   ```

3. **Run linting**:
   ```bash
   ruff check src/
   ruff format src/
   ```

4. **Update documentation** if needed

### Submitting

1. Push your branch to your fork
2. Create a Pull Request on GitHub
3. Fill out the PR template completely
4. Link any related issues

### PR Template

```markdown
## Summary
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests passing
- [ ] No new warnings
```

### Review Process

1. At least one maintainer must review the PR
2. All CI checks must pass
3. Conflicts must be resolved
4. Approval required before merge

## Reporting Bugs

### Before Submitting

1. Check the [issue tracker](https://github.com/your-repo/cursorBot/issues) for existing reports
2. Collect information about the bug:
   - OS and Python version
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages/logs

### Bug Report Template

```markdown
**Describe the bug**
A clear description of the bug.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Environment:**
- OS: [e.g., macOS 14.0]
- Python: [e.g., 3.11.5]
- CursorBot version: [e.g., 0.4.0]

**Additional context**
Any other context, screenshots, or logs.
```

## Suggesting Features

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Any alternative solutions you've considered.

**Additional context**
Any other context, mockups, or examples.
```

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- GitHub contributors page

Thank you for contributing to CursorBot!

---

## Questions?

Feel free to open an issue or reach out to the maintainers if you have any questions.
