# Pull Request

## Description

### What does this PR do?
<!-- Briefly describe what changes this PR includes -->

### Why is this needed?
<!-- Explain the problem it solves or the feature it adds -->

### How was this tested?
<!-- Describe how you tested the changes -->

## Type of Change

Check all that apply:

- [ ] **Bug fix** (non-breaking change which fixes an issue)
- [ ] **New feature** (non-breaking change which adds functionality)
- [ ] **Breaking change** (fix or feature that would cause existing functionality to not work as expected)
- [ ] **Documentation** (changes to documentation only)
- [ ] **Style** (formatting, white-space, etc.; no code changes)
- [ ] **Refactoring** (code change that neither fixes a bug nor adds a feature)
- [ ] **Performance improvement** (code change that improves performance)
- [ ] **Tests** (adding missing tests or correcting existing tests)
- [ ] **Configuration** (changes to build files, CI, etc.)

## Testing

### Tests Performed
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Tested with different log file types
- [ ] Tested with different LLM models

### Test Cases
<!-- Describe the specific test cases you performed -->
```
1. Test Case 1: [Description]
   - Input: [Describe the input]
   - Expected: [Expected result]
   - Actual: [Actual result]

2. Test Case 2: [Description]
   - Input: [Describe the input]
   - Expected: [Expected result]
   - Actual: [Actual result]
```

## Screenshots (if applicable)

### Before
<!-- Screenshots of previous state -->

### After
<!-- Screenshots of new state -->

## Configuration and Environment

### Development Environment
- [ ] Docker version: [e.g. 20.10.x]
- [ ] Docker Compose version: [e.g. 2.x.x]
- [ ] OS: [e.g. Windows 11, Ubuntu 20.04, macOS 12]
- [ ] GPU available: [Yes/No, model]

### LLM Models Tested
- [ ] qwen2.5:3b (default model)
- [ ] phi3:mini (lightweight model)
- [ ] llama3:8b (large model)
- [ ] Other: [specify]

## Checklist

Before submitting this PR, ensure that:

### Code
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes

### Documentation
- [ ] I have made corresponding changes to the documentation
- [ ] I have updated the README if necessary
- [ ] I have updated CONFIGURACION-MODELOS.md if applicable
- [ ] I have added docstrings to new functions

### Integration
- [ ] My changes don't break existing functionality
- [ ] I have tested the integration with other components
- [ ] Docker containers build correctly
- [ ] The application starts correctly with docker-compose

## Related Issues

### Closes Issues
<!-- Use "Closes #123" to automatically close issues -->
- Closes #

### Related to Issues
<!-- Use "Related to #123" for related issues -->
- Related to #

## Breaking Changes

<!-- If you marked "Breaking change" above, describe what breaks and how to migrate -->

### What breaks?
<!-- Describe what existing functionality may be affected -->

### How to migrate?
<!-- Describe the steps needed for users to update -->

## Additional Notes

### For Reviewers
<!-- Specific information for code reviewers -->

### Pending Items
<!-- List any pending work or known limitations -->

---

## Contact

If you have questions about this PR, please:
- Comment directly on the PR
- Mention @username in specific comments
- Open a discussion issue if it's something broader