---
name: Bug Report
about: Report a bug or issue with the system
title: '[BUG] '
labels: ['bug', 'needs-triage']
assignees: ''
---

# Bug Report

## Problem Description

### What happened?
<!-- Clearly describe what error occurred -->

### What did you expect to happen?
<!-- Describe the expected behavior -->

## Steps to Reproduce

1. 
2. 
3. 
4. 

## Screenshots/Videos

<!-- If possible, add screenshots or videos of the error -->

## Environment Information

### Operating System
- [ ] Windows 10/11
- [ ] macOS (version: )
- [ ] Linux (distribution: )

### Docker
- Docker version: 
- Docker Compose version: 

### Hardware
- Total RAM: 
- GPU: [ ] NVIDIA [ ] AMD [ ] None
- GPU model (if applicable): 

### Project Configuration
- LLM model used: 
- Project version: 
- Branch: 

## Logs and Errors

### System Logs
```
<!-- Paste relevant logs here -->
```

### Specific Error
```
<!-- Paste the exact error message here -->
```

### Docker Logs
```bash
# Run these commands and paste the results:
# docker-compose logs -f
# docker-compose ps
```

## Additional Information

### Does the problem always occur?
- [ ] Yes, always
- [ ] No, it's intermittent
- [ ] Only under certain conditions

### What file types does it occur with?
- [ ] Small files (< 1MB)
- [ ] Medium files (1-100MB)
- [ ] Large files (> 100MB)
- [ ] All file sizes

### When did the problem start?
- [ ] Since initial installation
- [ ] After an update
- [ ] After changing configuration
- [ ] Suddenly, with no apparent changes

## Attempted Solutions

<!-- What have you tried to solve the problem? -->

- [ ] Restart containers (`docker-compose restart`)
- [ ] Rebuild images (`docker-compose build --no-cache`)
- [ ] Clean volumes (`docker-compose down -v`)
- [ ] Check logs of all services
- [ ] Change LLM model
- [ ] Other: 

## Impact

### Severity
- [ ] Critical - Application doesn't work
- [ ] High - Important functionality doesn't work
- [ ] Medium - Minor functionality doesn't work
- [ ] Low - Cosmetic or minor issue

### Is there a workaround?
- [ ] Yes: 
- [ ] No

## Contact Information

Can we contact you for more information?
- [ ] Yes, through GitHub
- [ ] Yes, by email: 
- [ ] Not necessary

---

## Checklist (for reporter)

Before submitting this issue:

- [ ] I have searched existing issues to see if this was already reported
- [ ] I have followed the troubleshooting steps in the README
- [ ] I have included all relevant information
- [ ] I have verified this is a bug and not a configuration issue