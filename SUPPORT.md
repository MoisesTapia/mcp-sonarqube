# Support

Thank you for using SonarQube MCP! This document provides information on how to get help and support for the project.

## 📚 Documentation

Before seeking support, please check our comprehensive documentation:

### 📖 Primary Documentation
- **[README.md](README.md)** - Project overview and quick start guide
- **[DOCKER_SETUP.md](DOCKER_SETUP.md)** - Detailed Docker setup and deployment guide
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development and contribution guidelines
- **[SECURITY.md](SECURITY.md)** - Security policy and vulnerability reporting

### 🔧 Technical Documentation
- **Configuration Guide** - Environment setup and configuration options
- **API Documentation** - MCP tools and endpoints reference
- **Troubleshooting Guide** - Common issues and solutions
- **Performance Guide** - Optimization and monitoring tips

## 🆘 Getting Help

### 1. 🔍 Self-Help Resources

**Check Existing Issues:**
- Browse [GitHub Issues](https://github.com/username/sonarqube-mcp/issues) for similar problems
- Search [GitHub Discussions](https://github.com/username/sonarqube-mcp/discussions) for community Q&A
- Review [Closed Issues](https://github.com/username/sonarqube-mcp/issues?q=is%3Aissue+is%3Aclosed) for resolved problems

**Common Solutions:**
```bash
# Health check for troubleshooting
make health

# Configuration validation
make config-validate

# View service logs
make logs

# Resource monitoring
make monitor
```

### 2. 💬 Community Support

**GitHub Discussions** (Recommended)
- **Q&A**: General questions and help requests
- **Ideas**: Feature suggestions and discussions
- **Show and Tell**: Share your implementations and use cases
- **General**: Community chat and announcements

**Issue Tracker**
- **Bug Reports**: Use the bug report template
- **Feature Requests**: Use the feature request template
- **Documentation Issues**: Report documentation problems

### 3. 🚨 Priority Support

For urgent issues or enterprise support needs:

**Security Issues:**
- Follow our [Security Policy](SECURITY.md)
- Use private vulnerability reporting
- Email: security@sonarqube-mcp.com

**Critical Production Issues:**
- Create a GitHub issue with `critical` label
- Include detailed environment information
- Provide logs and error messages
- Email: support@sonarqube-mcp.com (if available)

## 📋 Support Request Guidelines

### 🐛 Reporting Bugs

When reporting bugs, please include:

**System Information:**
```bash
# Run this command and include output
make info

# Or provide manually:
- OS: [e.g., Ubuntu 20.04, macOS 12.0, Windows 11]
- Python Version: [e.g., 3.11.0]
- Docker Version: [e.g., 20.10.12]
- SonarQube Version: [e.g., 10.3.0]
- Project Version: [e.g., 1.0.0]
```

**Reproduction Steps:**
1. Clear step-by-step instructions
2. Expected vs actual behavior
3. Error messages and logs
4. Screenshots (if applicable)

**Configuration:**
```bash
# Sanitized configuration (remove sensitive data)
cat .env | grep -v PASSWORD | grep -v TOKEN | grep -v SECRET
```

### ❓ Asking Questions

**Good Questions Include:**
- Clear description of what you're trying to achieve
- What you've already tried
- Specific error messages or unexpected behavior
- Relevant configuration and environment details

**Question Template:**
```markdown
## What I'm trying to do
[Clear description of your goal]

## What I've tried
[Steps you've already taken]

## Current behavior
[What's happening now]

## Expected behavior
[What you expected to happen]

## Environment
[System and configuration details]
```

### 💡 Feature Requests

When requesting features:
- Explain the use case and motivation
- Describe the proposed solution
- Consider alternative approaches
- Assess the impact and priority

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 🐳 Docker Issues

**Services won't start:**
```bash
# Check Docker daemon
docker info

# Check service health
make health

# View service logs
make logs

# Restart services
make restart
```

**Port conflicts:**
```bash
# Check port usage
netstat -tulpn | grep :8501

# Use development ports
make dev  # Uses ports 8080, 8443 instead of 80, 443
```

**Resource issues:**
```bash
# Monitor resources
make monitor

# Check Docker resources
docker system df
docker stats
```

#### 🔗 SonarQube Connection Issues

**Authentication problems:**
```bash
# Validate configuration
make config-validate

# Test SonarQube connection
curl -u "your_token:" "https://your-sonarqube.com/api/system/status"
```

**Network connectivity:**
```bash
# Test network connectivity
ping your-sonarqube-server.com
curl -I https://your-sonarqube-server.com

# Check firewall and proxy settings
```

#### 🎨 Streamlit Issues

**App won't load:**
```bash
# Check Streamlit health
curl http://localhost:8501/_stcore/health

# View Streamlit logs
docker logs sonarqube-streamlit-app

# Restart Streamlit service
docker restart sonarqube-streamlit-app
```

**Configuration problems:**
```bash
# Validate Streamlit configuration
bash docker/scripts/validate-config.sh

# Check environment variables
docker exec sonarqube-streamlit-app env | grep STREAMLIT
```

### 🔍 Debugging Tools

**Health Checks:**
```bash
# Overall system health
make health

# Individual service health
bash docker/scripts/health-check.sh

# Resource monitoring
bash docker/scripts/resource-monitor.sh
```

**Log Analysis:**
```bash
# Aggregate logs
bash docker/scripts/log-aggregator.sh collect

# Search for errors
bash docker/scripts/log-aggregator.sh search error

# Follow logs in real-time
make logs
```

**Configuration Validation:**
```bash
# Validate current configuration
make config-validate

# Validate specific environment
bash docker/scripts/validate-config.sh docker/environments/.env.production
```

## 📞 Contact Information

### 🌐 Online Resources
- **GitHub Repository**: https://github.com/username/sonarqube-mcp
- **Documentation**: [Link to docs site if available]
- **Community Forum**: [Link if available]

### 📧 Email Support
- **General Support**: support@sonarqube-mcp.com
- **Security Issues**: security@sonarqube-mcp.com
- **Business Inquiries**: business@sonarqube-mcp.com

### 💬 Community Channels
- **GitHub Discussions**: For Q&A and community support
- **Issue Tracker**: For bug reports and feature requests
- **Discord/Slack**: [Links if available]

## 🕐 Response Times

### Community Support (GitHub)
- **Questions**: Usually within 24-48 hours
- **Bug Reports**: Within 1-3 business days
- **Feature Requests**: Within 1 week for initial response

### Priority Support
- **Security Issues**: Within 24 hours
- **Critical Bugs**: Within 24-48 hours
- **General Inquiries**: Within 1-2 business days

*Note: Response times may vary based on complexity and maintainer availability.*

## 🤝 Community Guidelines

When seeking support:

### ✅ Do:
- Search existing issues and discussions first
- Provide clear, detailed information
- Use appropriate templates and labels
- Be patient and respectful
- Follow up with additional information if requested
- Share solutions that work for you

### ❌ Don't:
- Create duplicate issues
- Demand immediate responses
- Share sensitive information publicly
- Use inappropriate language or behavior
- Spam multiple channels with the same request

## 🎓 Learning Resources

### 📚 Educational Content
- **SonarQube Documentation**: https://docs.sonarqube.org/
- **Docker Documentation**: https://docs.docker.com/
- **Streamlit Documentation**: https://docs.streamlit.io/
- **FastMCP Documentation**: [Link if available]

### 🎥 Tutorials and Guides
- **Getting Started Video**: [Link if available]
- **Configuration Tutorial**: [Link if available]
- **Deployment Guide**: [Link if available]
- **Best Practices**: [Link if available]

### 🛠️ Development Resources
- **API Reference**: [Link to API docs]
- **Development Setup**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Architecture Overview**: [Link if available]
- **Testing Guide**: [Link if available]

## 🔄 Support Workflow

### 1. **Issue Identification**
- Clearly identify the problem or question
- Gather relevant information and logs
- Check existing resources and documentation

### 2. **Initial Support**
- Search existing issues and discussions
- Try common troubleshooting steps
- Review documentation and guides

### 3. **Community Engagement**
- Create detailed issue or discussion post
- Engage with community responses
- Provide additional information as requested

### 4. **Resolution**
- Implement suggested solutions
- Test and verify fixes
- Share results with the community
- Close issues when resolved

### 5. **Follow-up**
- Update documentation if needed
- Share learnings with others
- Consider contributing improvements

## 🏆 Recognition

We appreciate community members who:
- Help others in discussions and issues
- Contribute to documentation and guides
- Share their experiences and solutions
- Provide constructive feedback and suggestions

Active community supporters may be invited to join our contributor recognition program.

## 📈 Improving Support

We continuously work to improve our support:

### Recent Improvements
- Enhanced documentation and troubleshooting guides
- Improved issue templates and workflows
- Better response time tracking
- Community recognition programs

### Planned Improvements
- Interactive troubleshooting tools
- Video tutorials and guides
- Community mentorship programs
- Enhanced monitoring and alerting

## 📝 Feedback

Help us improve our support:
- **Support Quality**: Rate your support experience
- **Documentation**: Suggest improvements to guides
- **Process**: Recommend workflow enhancements
- **Tools**: Suggest better support tools

**Feedback Channels:**
- GitHub Discussions feedback section
- Support survey (if available)
- Direct email to support team

---

**Thank you for being part of the SonarQube MCP community!** 🚀

Your questions, feedback, and contributions help make this project better for everyone.