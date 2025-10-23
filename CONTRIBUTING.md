# Contributing to SonarQube MCP

Thank you for your interest in contributing to SonarQube MCP! We welcome contributions from the community and are excited to work with you.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Development Standards](#development-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### 🚀 Quick Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/sonarqube-mcp.git
   cd sonarqube-mcp
   ```
3. **Set up development environment**:
   ```bash
   make quickstart
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### 🔧 Development Environment Options

**Docker Development (Recommended):**
```bash
make dev                    # Start development environment
make test                   # Run tests
make lint                   # Run linting
make format                 # Format code
```

**Manual Python Setup:**
```bash
pip install -r requirements-dev.txt
pre-commit install
pytest
```

## Development Setup

### Prerequisites

- **Python 3.9+**
- **Docker & Docker Compose** (recommended)
- **Git**
- **SonarQube server** (for integration testing)

### Environment Configuration

1. **Copy environment template**:
   ```bash
   cp docker/environments/.env.development .env
   ```

2. **Configure SonarQube connection**:
   ```bash
   # Edit .env file
   SONARQUBE_TOKEN=your_sonarqube_token_here
   SONARQUBE_URL=https://your-sonarqube-instance.com
   ```

3. **Generate secrets** (for Docker development):
   ```bash
   bash docker/scripts/manage-secrets.sh generate
   ```

### Verify Setup

```bash
# Check service health
make health

# Run tests to verify everything works
make test

# Check code quality
make lint
```

## Contributing Guidelines

### 🎯 Types of Contributions

We welcome various types of contributions:

- **🐛 Bug Reports**: Help us identify and fix issues
- **✨ Feature Requests**: Suggest new functionality
- **🔧 Code Contributions**: Implement features or fix bugs
- **📚 Documentation**: Improve or add documentation
- **🧪 Testing**: Add or improve test coverage
- **🎨 UI/UX Improvements**: Enhance the Streamlit interface
- **🐳 DevOps**: Improve Docker configuration or CI/CD
- **🔒 Security**: Identify and fix security vulnerabilities

### 🌟 Good First Issues

Look for issues labeled with:
- `good first issue`: Perfect for newcomers
- `help wanted`: We need community help
- `documentation`: Documentation improvements
- `testing`: Test coverage improvements

### 📝 Before You Start

1. **Check existing issues** to avoid duplicate work
2. **Create an issue** for significant changes to discuss approach
3. **Comment on issues** you'd like to work on
4. **Ask questions** if anything is unclear

## Pull Request Process

### 1. 🔄 Preparation

```bash
# Ensure your fork is up to date
git remote add upstream https://github.com/original/sonarqube-mcp.git
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. 🛠️ Development

```bash
# Make your changes
# Follow coding standards (see below)

# Test your changes
make test
make lint
make format

# Commit with clear messages
git add .
git commit -m "feat: add new security analysis feature

- Implement vulnerability risk scoring
- Add security recommendations
- Update tests and documentation
- Closes #123"
```

### 3. 📤 Submission

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
# Use the PR template
# Link related issues
```

### 4. 🔍 Review Process

- **Automated checks** must pass (CI/CD, tests, linting)
- **Code review** by maintainers
- **Address feedback** promptly
- **Squash commits** if requested
- **Merge** after approval

### 📋 Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Related Issues
Closes #123
Related to #456

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] All tests pass

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings introduced
- [ ] Backward compatibility maintained
```

## Issue Guidelines

### 🐛 Bug Reports

Use the bug report template and include:

- **Clear title** describing the issue
- **Steps to reproduce** the problem
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, Docker version)
- **Error messages** and logs
- **Screenshots** if applicable

### ✨ Feature Requests

Use the feature request template and include:

- **Clear description** of the proposed feature
- **Use case** and motivation
- **Proposed solution** (if you have ideas)
- **Alternative solutions** considered
- **Additional context** or examples

### 🔒 Security Issues

**Do not create public issues for security vulnerabilities!**

Instead:
- Follow our [Security Policy](SECURITY.md)
- Use GitHub's private vulnerability reporting
- Email security@sonarqube-mcp.com

## Development Standards

### 🐍 Python Code Standards

**Style Guidelines:**
- Follow **PEP 8** style guide
- Use **Black** for code formatting
- Use **Ruff** for linting
- Use **MyPy** for type checking

**Code Quality:**
```bash
# Format code
black src tests

# Check linting
ruff check src tests

# Type checking
mypy src

# All quality checks
make lint
```

**Code Structure:**
- Use **type hints** for all public interfaces
- Write **docstrings** for all public functions/classes
- Follow **SOLID principles**
- Keep functions **small and focused**
- Use **meaningful variable names**

### 🧪 Testing Standards

**Test Coverage:**
- Maintain **80%+ test coverage**
- Write tests for **all new features**
- Update tests for **modified functionality**
- Include **edge cases** and **error conditions**

**Test Types:**
```bash
# Unit tests (fast, isolated)
pytest tests/unit/

# Integration tests (with external services)
pytest tests/integration/

# UI tests (end-to-end workflows)
pytest tests/ui/

# All tests
pytest
```

**Test Guidelines:**
- Use **descriptive test names**
- Follow **AAA pattern** (Arrange, Act, Assert)
- Use **fixtures** for common setup
- **Mock external dependencies** in unit tests
- Test **both success and failure paths**

### 🐳 Docker Standards

**Dockerfile Best Practices:**
- Use **multi-stage builds**
- Run as **non-root user**
- Minimize **image layers**
- Use **specific base image tags**
- Include **health checks**

**Docker Compose:**
- Use **environment-specific overrides**
- Define **resource limits**
- Include **health checks**
- Use **named volumes** for persistence
- Implement **proper networking**

### 📚 Documentation Standards

**Code Documentation:**
- **Docstrings** for all public APIs
- **Type hints** for function signatures
- **Inline comments** for complex logic
- **README updates** for new features

**User Documentation:**
- Update **README.md** for user-facing changes
- Add **examples** for new features
- Update **configuration documentation**
- Include **troubleshooting** information

## Testing Requirements

### 🧪 Required Tests

**For New Features:**
- [ ] Unit tests for core logic
- [ ] Integration tests for external interactions
- [ ] UI tests for user-facing features
- [ ] Error handling tests
- [ ] Performance tests (if applicable)

**For Bug Fixes:**
- [ ] Regression test reproducing the bug
- [ ] Fix verification test
- [ ] Related functionality tests

### 🚀 Test Execution

```bash
# Run all tests
make test

# Run specific test categories
pytest tests/unit/                    # Unit tests only
pytest tests/integration/             # Integration tests
pytest tests/ui/                      # UI workflow tests
pytest -k "security"                  # Security-related tests

# Run with coverage
pytest --cov=src --cov-report=html

# Run in Docker
make test-docker
```

### 📊 Performance Testing

For performance-critical changes:
- **Benchmark** before and after changes
- **Profile** code for bottlenecks
- **Load test** API endpoints
- **Monitor** resource usage

## Documentation

### 📝 Documentation Types

**Code Documentation:**
- **Docstrings**: All public functions and classes
- **Type hints**: Function signatures and return types
- **Comments**: Complex algorithms and business logic

**User Documentation:**
- **README.md**: Project overview and quick start
- **DOCKER_SETUP.md**: Detailed Docker instructions
- **API documentation**: MCP tools and endpoints
- **Configuration guides**: Environment setup

**Developer Documentation:**
- **CONTRIBUTING.md**: This file
- **Architecture docs**: System design and patterns
- **Deployment guides**: Production setup instructions

### 🔄 Documentation Updates

When contributing:
- [ ] Update relevant documentation
- [ ] Add examples for new features
- [ ] Update configuration references
- [ ] Include troubleshooting information
- [ ] Review for clarity and accuracy

## Community

### 💬 Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community chat
- **Pull Requests**: Code review and collaboration
- **Security**: security@sonarqube-mcp.com

### 🤝 Getting Help

**For Development Questions:**
1. Check existing **documentation**
2. Search **GitHub issues** and discussions
3. Create a **new discussion** with your question
4. Tag relevant **maintainers** if needed

**For Bug Reports:**
1. Search **existing issues** first
2. Use the **bug report template**
3. Provide **detailed information**
4. Be responsive to **follow-up questions**

### 🏆 Recognition

We appreciate all contributions! Contributors will be:
- **Listed** in project documentation
- **Credited** in release notes
- **Invited** to join the contributors team (for regular contributors)
- **Mentioned** in project communications

## Development Workflow

### 🔄 Typical Workflow

1. **Find/Create Issue**: Identify work to be done
2. **Discuss Approach**: Comment on issue with your plan
3. **Fork & Branch**: Create feature branch
4. **Develop**: Write code following standards
5. **Test**: Ensure all tests pass
6. **Document**: Update relevant documentation
7. **Submit PR**: Create pull request with clear description
8. **Review**: Address feedback from maintainers
9. **Merge**: Celebrate your contribution! 🎉

### 🚀 Release Process

**For Maintainers:**
1. **Version Bump**: Update version numbers
2. **Changelog**: Update CHANGELOG.md
3. **Testing**: Full test suite execution
4. **Documentation**: Ensure docs are current
5. **Release**: Create GitHub release
6. **Docker Images**: Build and push new images
7. **Announcements**: Notify community

## Questions?

If you have questions about contributing:

1. **Check the documentation** first
2. **Search existing issues** and discussions
3. **Create a discussion** for general questions
4. **Contact maintainers** for specific guidance

Thank you for contributing to SonarQube MCP! 🚀