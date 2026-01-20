# Contributing to SkyWatcher Controller

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How to Contribute](#how-to-contribute)
3. [Development Setup](#development-setup)
4. [Testing](#testing)
5. [Coding Standards](#coding-standards)
6. [Pull Request Process](#pull-request-process)
7. [Reporting Bugs](#reporting-bugs)
8. [Suggesting Features](#suggesting-features)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors.

### Expected Behavior

- Be respectful and considerate
- Welcome newcomers and help them learn
- Accept constructive criticism gracefully
- Focus on what's best for the project and community

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Trolling or insulting/derogatory comments
- Publishing others' private information
- Other conduct inappropriate in a professional setting

---

## How to Contribute

### Ways to Contribute

- **Report Bugs**: File detailed bug reports with steps to reproduce
- **Suggest Features**: Propose new features or improvements
- **Submit Fixes**: Fix bugs or implement features
- **Improve Documentation**: Enhance or clarify documentation
- **Test**: Test on different platforms and configurations
- **Review**: Review pull requests from others

### First-Time Contributors

Look for issues tagged with:
- `good first issue` - Easy fixes for newcomers
- `help wanted` - Issues where help is needed
- `documentation` - Documentation improvements

---

## Development Setup

### Prerequisites

- Python 3.7 or higher
- Git
- Text editor or IDE
- Virtual environment tool

### Setup Steps

1. **Fork the Repository**
   ```bash
   # On GitHub, click "Fork" button
   # Then clone your fork
   git clone https://github.com/YOUR_USERNAME/skywatcher-controller.git
   cd skywatcher-controller
   ```

2. **Add Upstream Remote**
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/skywatcher-controller.git
   ```

3. **Create Virtual Environment**
   ```bash
   python -m venv venv
   
   # Activate it
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

4. **Install Dependencies**
   ```bash
   # For development
   pip install -e .
   
   # For testing (when available)
   pip install pytest pytest-cov
   
   # For GUI themes (optional)
   pip install ttkbootstrap
   ```

5. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Project Structure

```
skywatcher-controller/
├── StarCommandGUI.py       # GUI application
├── StarCommandCLI.py       # CLI application
├── docs/                   # Documentation
│   ├── INSTALL.md
│   ├── USER_GUIDE.md
│   ├── TROUBLESHOOTING.md
│   └── PROTOCOL_REFERENCE.md
├── tests/                  # Test files (when added)
├── setup.py                # Package configuration
├── requirements.txt        # Dependencies
└── README.md              # Project overview
```

---

## Testing

### Manual Testing

Before submitting changes:

1. **Test Both Applications**
   ```bash
   # Test GUI
   python StarCommandGUI.py
   
   # Test CLI
   python StarCommandCLI.py
   ```

2. **Test on Multiple Platforms** (if possible)
   - Windows
   - Linux (Ubuntu/Debian preferred)
   - macOS

3. **Test Without Hardware**
   - Connection should fail gracefully
   - No crashes on timeout
   - Error messages should be clear

4. **Test With Hardware**
   - All movement directions
   - Speed changes
   - Emergency stop
   - Position display
   - Preset positions
   - Configuration saving

### Automated Testing

When test suite is added:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_protocol.py
```

### Testing Checklist

- [ ] Code runs without errors
- [ ] New features work as intended
- [ ] Existing features still work
- [ ] Error handling works correctly
- [ ] Configuration saves and loads
- [ ] Documentation updated
- [ ] No new warnings or deprecations

---

## Coding Standards

### Python Style

Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with these specifics:

**Indentation:**
- 4 spaces (no tabs)

**Line Length:**
- Maximum 100 characters (soft limit)
- Maximum 120 characters (hard limit)

**Naming Conventions:**
```python
# Classes: PascalCase
class SkyWatcherProtocol:
    pass

# Functions/Methods: snake_case
def send_command(self, command):
    pass

# Constants: UPPER_CASE
DEFAULT_PORT = 11880

# Private methods: _leading_underscore
def _internal_method(self):
    pass
```

**Docstrings:**
```python
def function_name(param1, param2):
    """
    Brief description of function.
    
    Args:
        param1 (type): Description
        param2 (type): Description
    
    Returns:
        type: Description
    
    Raises:
        ExceptionType: When and why
    """
    pass
```

### Code Organization

**Imports:**
```python
# Standard library
import os
import sys
import time

# Third-party
import tkinter as tk
from tkinter import ttk

# Local
from .module import function
```

**Class Organization:**
```python
class Example:
    """Class docstring"""
    
    # Class variables
    CLASS_CONSTANT = "value"
    
    def __init__(self):
        """Constructor"""
        pass
    
    # Public methods
    def public_method(self):
        """Public method"""
        pass
    
    # Private methods
    def _private_method(self):
        """Private method"""
        pass
```

### Comments

```python
# Good: Explain WHY, not WHAT
# Calculate step period based on timer frequency and desired speed
step_period = int((timer_freq * 360.0) / (speed * cpr))

# Bad: Redundant comment
# Calculate step period
step_period = int((timer_freq * 360.0) / (speed * cpr))
```

### Error Handling

```python
# Be specific with exceptions
try:
    value = int(user_input)
except ValueError:
    print("Invalid integer")

# Provide helpful error messages
if not self.protocol:
    raise ConnectionError("Not connected to telescope. Call connect() first.")

# Clean up resources
try:
    file = open('data.txt')
    # ... use file
finally:
    file.close()
```

---

## Pull Request Process

### Before Submitting

1. **Update Your Branch**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Test Thoroughly**
   - Run all tests
   - Test manually
   - Check for regressions

3. **Update Documentation**
   - Update relevant docs
   - Add docstrings
   - Update CHANGELOG if exists

4. **Commit Messages**
   ```
   Short summary (50 chars or less)
   
   More detailed explanation if needed. Wrap at 72 characters.
   Explain what and why, not how.
   
   - Bullet points are okay
   - Use present tense: "Add feature" not "Added feature"
   - Reference issues: "Fixes #123"
   ```

### Submitting Pull Request

1. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request**
   - Go to GitHub
   - Click "New Pull Request"
   - Select your feature branch
   - Fill out template

3. **PR Description Should Include:**
   - Summary of changes
   - Motivation and context
   - Testing performed
   - Screenshots (if UI changes)
   - Related issues

4. **Review Process**
   - Respond to feedback promptly
   - Make requested changes
   - Push updates to same branch
   - Request re-review when ready

### Merge Criteria

- All tests pass
- Code review approved
- Documentation updated
- No merge conflicts
- Follows coding standards

---

## Reporting Bugs

### Before Reporting

1. **Search Existing Issues**
   - Check if already reported
   - Add comment if you have new info

2. **Verify It's a Bug**
   - Test on latest version
   - Try without modifications
   - Check if it's a configuration issue

### Bug Report Template

```markdown
**Description**
Clear description of the bug

**Steps to Reproduce**
1. Start application
2. Click button X
3. See error

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: [e.g., Windows 10, Ubuntu 22.04]
- Python version: [e.g., 3.10.5]
- Application: [GUI or CLI]
- Mount model: [e.g., GTi 150P]

**Logs**
```
Relevant log excerpts (enable debug mode)
```

**Screenshots**
If applicable

**Additional Context**
Any other relevant information
```

### Priority Levels

- **Critical**: Crash, data loss, security issue
- **High**: Major feature broken, common workflow blocked
- **Medium**: Minor feature broken, workaround exists
- **Low**: Cosmetic issue, rare edge case

---

## Suggesting Features

### Before Suggesting

1. **Check Existing Requests**
   - Search issues and discussions
   - Vote/comment on existing requests

2. **Consider Scope**
   - Does it fit project goals?
   - Would others benefit?
   - Is it feasible?

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
Clear description of the problem

**Proposed Solution**
Describe how you'd like it to work

**Alternatives Considered**
Other approaches you've thought about

**Use Cases**
Who would use this and how?

**Implementation Notes**
Technical details if you have ideas

**Mockups/Examples**
Screenshots, diagrams, or examples if helpful
```

---

## Development Guidelines

### Protocol Changes

Changes to telescope protocol handling:

1. **Document Thoroughly**
   - Update PROTOCOL_REFERENCE.md
   - Add inline comments
   - Explain reasoning

2. **Maintain Compatibility**
   - Don't break existing functionality
   - Version detection if needed
   - Graceful degradation

3. **Test Extensively**
   - Test with real hardware
   - Test edge cases
   - Test error conditions

### GUI Changes

1. **Consistent Layout**
   - Follow existing patterns
   - Use tabs appropriately
   - Maintain spacing/padding

2. **Accessibility**
   - Keyboard navigation
   - Logical tab order
   - Clear labels

3. **Theme Support**
   - Test with and without ttkbootstrap
   - Test light and dark themes
   - Don't hardcode colors

### Configuration Changes

1. **Backward Compatibility**
   - Handle old config files
   - Provide migration if needed
   - Set sensible defaults

2. **Validation**
   - Validate all inputs
   - Provide error messages
   - Don't crash on bad config

### Documentation Changes

1. **Clear and Concise**
   - Use simple language
   - Provide examples
   - Keep it up-to-date

2. **Formatting**
   - Use Markdown correctly
   - Include code blocks
   - Add screenshots where helpful

---

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project README

Significant contributions may earn you:
- Collaborator status
- Listed as author
- Special thanks in releases

---

## Questions?

- **GitHub Discussions**: For questions and help
- **GitHub Issues**: For bugs and features only
- **Email**: [if provided]

---

## License

By contributing, you agree that your contributions will be licensed under the same MIT License that covers the project.

---

Thank you for contributing! 🎉

Clear skies! 🔭
