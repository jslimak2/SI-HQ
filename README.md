# ***Post*9**

### **Stop Betting. Start Investing.**

---

At ***Post*9**, we merge the passion of sports with the precision of data science. Our platform is built for the sports investor, offering advanced analytics, predictive modeling, and sophisticated simulation tools to give you an edge. We go beyond simple stats, uncovering hidden opportunities and developing investment strategies that are as dynamic as the games themselves. Whether you're a seasoned investor or new to the field, ***Post*9** equips you with the insights to turn your sports knowledge into strategic success.

## 🚀 Getting Started

### Ready for Production? (Recommended)
```bash
# 1. Copy configuration template
cp .env.production .env

# 2. Update .env with your API keys (see PRODUCTION_SETUP_GUIDE.md)
# 3. Test your setup
python deploy_production.py --check-only

# 4. Start production server
cd dashboard && python app.py
```

### Just Exploring? (Demo Mode)
```bash
# Use demo configuration (fake data)
cp .env.demo .env
cd dashboard && python app.py
```

## 📖 Documentation

### 🚀 Production Setup
- **[Production Setup Guide](PRODUCTION_SETUP_GUIDE.md)** - **NEW** Complete step-by-step production configuration  
- **[Quick Production Deployment](QUICK_PRODUCTION_DEPLOYMENT.md)** - 30 minutes to production
- **[Deployment Guide](DEPLOYMENT.md)** - Advanced deployment options

### Quick Start
- **[Quick Reference Guide](QUICK_REFERENCE_GUIDE.md)** - Get started in 5 minutes
- **[Architecture Overview](ARCHITECTURE_AND_SYSTEM_DESIGN.md)** - Complete system documentation
- **[Schema Documentation](SCHEMA_DOCUMENTATION.md)** - **NEW v2.0** Standardized data models
- **[Demo Mode Control](DEMO_MODE_CONTROL.md)** - **NEW** Disable demo features for production validation

### Core Concepts
- **Models** 🤖 - AI-powered prediction engines for sports outcomes
- **Strategies** 📋 - Intelligent rules for when and how to invest
- **Investors** 🚀 - Automated investors that execute your strategies 24/7

### Production Ready Features ✨ **NEW**
- **Production Mode Validation** - Set `DISABLE_DEMO_MODE=true` to identify fully functional features
- **Real Data Only** - Force the application to use production data and fail fast on missing configuration
- **Visual Status Indicators** - Clear UI indicators show demo vs production status

### Schema & Data Models ✨ **NEW**
- **[Schema v2.0 Documentation](SCHEMA_DOCUMENTATION.md)** - Complete schema reference
- **Model Schema** - Enhanced ML model tracking with performance metrics
- **Investor Schema** - Comprehensive investor management with risk controls
- **Strategy Schema** - Advanced strategy configuration and tracking

### Detailed Documentation
- [Architecture & System Design](ARCHITECTURE_AND_SYSTEM_DESIGN.md) - Comprehensive technical documentation with Mermaid diagrams
- [ML System Documentation](ML_SYSTEM_DOCUMENTATION.md) - Machine learning pipeline details
- [Strategy & Investor Design Analysis](STRATEGY_AND_BOT_DESIGN_ANALYSIS.md) - Design patterns and best practices
- [Training Queue Implementation](TRAINING_QUEUE_IMPLEMENTATION.md) - Model training workflow
- [Investment Caching](INVESTMENT_CACHING_README.md) - Performance optimization
- [Deployment Guide](DEPLOYMENT.md) - Production setup instructions
- [Demo Mode Control](DEMO_MODE_CONTROL.md) - **NEW** Easy option to disable demo features

---

**Last Updated**: 9/13/2025
