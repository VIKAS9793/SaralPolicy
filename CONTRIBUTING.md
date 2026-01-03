# Contributing to SaralPolicy

Thank you for your interest in contributing to SaralPolicy! We welcome contributions from the community to help make insurance documents more understandable for everyone.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)

## 🤝 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of background or identity.

### Our Standards

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

## 🎯 How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

**When submitting a bug report, include:**
- Clear description of the issue
- Steps to reproduce the behavior
- Expected vs actual behavior
- Screenshots (if applicable)
- Environment details (OS, Python version, Ollama version)
- Relevant log output

### Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:
- Clear use case and motivation
- Detailed description of the proposed feature
- Examples of how it would work
- Any alternative solutions considered

### Contributing Code

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following our coding standards
3. **Add tests** for any new functionality
4. **Update documentation** as needed
5. **Ensure all tests pass** before submitting
6. **Submit a pull request** with a clear description

## 🛠️ Development Setup

### Prerequisites

- Python 3.9 or higher
- Ollama installed and running
- Git for version control

### Setup Steps

1. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/SaralPolicy.git
   cd SaralPolicy
   ```
   
   **Note:** Replace `YOUR-USERNAME` with your GitHub username after forking.

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Setup Ollama models:**
   ```bash
   ollama pull gemma2:2b
   ollama pull nomic-embed-text
   ```

5. **Index IRDAI knowledge base:**
   ```bash
   python scripts/index_irdai_knowledge.py
   ```

6. **Run tests:**
   ```bash
   python -m pytest tests/
   ```

## 🔄 Pull Request Process

1. **Update your fork** with the latest from main:
   ```bash
   git fetch upstream
   git merge upstream/main
   ```

2. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes** and commit:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

4. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request** with:
   - Clear title describing the change
   - Detailed description of what and why
   - References to related issues
   - Screenshots/GIFs if UI changes
   - Test results

6. **Wait for review** - maintainers will review and provide feedback

### Commit Message Convention

We follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Adding or updating tests
- `refactor:` Code refactoring
- `style:` Formatting changes
- `chore:` Maintenance tasks

**Examples:**
```
feat: add document comparison feature
fix: resolve ChromaDB connection timeout
docs: update RAG implementation guide
test: add integration tests for Q&A endpoint
```

## 📝 Coding Standards

### Python Code Style

- Follow **PEP 8** style guide
- Use **type hints** where appropriate
- Write **docstrings** for functions and classes
- Keep functions small and focused
- Use meaningful variable names

**Example:**
```python
def analyze_policy(text: str, policy_type: str) -> Dict[str, Any]:
    """
    Analyze insurance policy document using RAG.
    
    Args:
        text: Policy document text
        policy_type: Type of insurance (health/motor/life)
        
    Returns:
        Dictionary containing analysis results
    """
    # Implementation
    pass
```

### Code Organization

- Keep related code in appropriate service files
- Use modular design patterns
- Avoid circular dependencies
- Follow existing project structure

### Error Handling

- Use specific exception types
- Provide helpful error messages
- Log errors appropriately
- Handle edge cases gracefully

## 🧪 Testing Guidelines

### Test Requirements

- **Write tests** for all new features
- **Update tests** when modifying existing code
- Ensure **100% of critical path** is tested
- Include both **unit and integration tests**

### Running Tests

```bash
# Run all tests (Recommended)
python -m pytest tests/

# Run specific integration test
python -m pytest tests/test_rag_citations.py
```

### Test Coverage

- Aim for high test coverage on critical components
- Test happy paths and error scenarios
- Include edge cases
- Mock external dependencies (Ollama API)

## 📚 Documentation

### What to Document

- **Code comments** for complex logic
- **Docstrings** for functions and classes
- **README updates** for new features
- **API documentation** for new endpoints
- **User guides** for significant changes

### Documentation Standards

- Use clear, concise language
- Include code examples
- Add screenshots for UI changes
- Keep documentation up-to-date with code

## 🌟 Areas for Contribution

We especially welcome contributions in these areas:

### High Priority
- Additional IRDAI regulatory knowledge documents
- Support for more insurance types (travel, property, etc.)
- Enhanced Hindi translation capabilities
- Performance optimizations
- Additional test coverage

### Medium Priority
- UI/UX improvements
- Additional evaluation metrics
- Better error handling and logging
- Documentation improvements
- Integration with more LLM models

### Nice to Have
- Mobile app support
- Additional language support (regional languages)
- Advanced analytics dashboard
- Export features (PDF, CSV)
- Browser extensions

## 🔒 Security

If you discover a security vulnerability, please email **vikassahani17@gmail.com** instead of using the issue tracker. Security issues will be handled privately and fixed before public disclosure.

## 📞 Questions?

- **GitHub Issues:** For bugs and feature requests
- **Email:** vikassahani17@gmail.com
- **LinkedIn:** [Vikas Sahani](https://www.linkedin.com/in/vikas-sahani-727420358)

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to SaralPolicy!** 🙏

Your efforts help make insurance more transparent and understandable for millions of people.
