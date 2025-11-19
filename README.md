# NASDAQ Stock Agent

AI-powered stock analysis and investment recommendations using Langchain, Anthropic Claude, and real-time market data. Built with FastAPI and designed for both REST API and Agent-to-Agent (A2A) communication via the NEST framework.

## Features

- **Natural Language Processing**: Query stocks using company names or natural language
- **Real-time Market Data**: Current prices, volume, and 6-month historical data via Yahoo Finance
- **AI-Powered Analysis**: Investment recommendations with confidence scores using Claude
- **Comprehensive Logging**: Full audit trails and performance monitoring
- **Agent Registry**: Discoverable agent capabilities and information
- **A2A Communication**: NEST framework integration for agent-to-agent interactions
- **REST API**: Full-featured REST endpoints with OpenAPI documentation

## Quick Start

### Prerequisites

- Python 3.9+ (Python 3.10+ recommended for MCP support)
- Anthropic API key
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/DataSup-Engineer/nasdaq-agent.git
cd nasdaq-agent
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
nano .env  # Edit with your configuration
```

5. Set required environment variables:
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
ANTHROPIC_MODEL=claude-3-haiku-20240307

# Optional - NEST A2A
NEST_ENABLED=true
NEST_PORT=6000
NEST_PUBLIC_URL=http://localhost:6000
```

6. Run the application:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## Usage

### REST API

**Analyze a stock:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "What do you think about Apple stock?"}'
```

**Check health:**
```bash
curl http://localhost:8000/health
```

**View API documentation:**
Open `http://localhost:8000/docs` in your browser

### A2A Communication (NEST)

When NEST is enabled, the agent can communicate with other agents:

```bash
curl -X POST http://localhost:6000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": {
      "type": "text",
      "text": "Should I buy Tesla?"
    },
    "conversation_id": "test-123"
  }'
```

**Available A2A commands:**
- `/help` - Show available commands
- `/status` - Check agent status
- `/ping` - Test connectivity
- Stock queries - Natural language or ticker symbols

## Example Queries

- "What do you think about Apple stock?"
- "Should I buy Tesla?"
- "Analyze Microsoft"
- "AAPL"
- "Tell me about NVDA"

## Response Format

All analysis responses include:
- **Recommendation**: Buy/Hold/Sell
- **Confidence Score**: 0-100
- **Current Price**: Real-time market data
- **Market Data**: Volume, 52-week range, historical performance
- **Reasoning**: Detailed analysis and key factors
- **Risk Assessment**: Identified risks and considerations

## Architecture

```
nasdaq-agent/
├── src/
│   ├── agents/          # LangChain agent implementations
│   ├── api/             # FastAPI application and routers
│   ├── config/          # Configuration management
│   ├── core/            # Core dependencies and utilities
│   ├── mcp/             # Model Context Protocol integration
│   ├── models/          # Data models and schemas
│   ├── nest/            # NEST A2A framework integration
│   └── services/        # Business logic and external services
├── tests/               # Test suite
├── logs/                # Application logs
├── main.py              # Application entry point
└── requirements.txt     # Python dependencies
```

## Configuration

### Environment Variables

**Required:**
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `ANTHROPIC_MODEL` - Claude model to use (default: claude-3-haiku-20240307)

**Application:**
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8000)
- `DEBUG` - Debug mode (default: false)

**NEST A2A:**
- `NEST_ENABLED` - Enable NEST integration (default: false)
- `NEST_PORT` - A2A server port (default: 6000)
- `NEST_PUBLIC_URL` - Public URL for A2A endpoint
- `NEST_REGISTRY_URL` - Agent registry URL
- `NEST_AGENT_ID` - Unique agent identifier
- `NEST_AGENT_NAME` - Human-readable agent name

See `.env.example` for complete configuration options.

## Deployment

### AWS EC2 Deployment

For production deployment on AWS EC2, see the comprehensive [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

**Quick deployment:**
```bash
# On EC2 instance
git clone https://github.com/DataSup-Engineer/nasdaq-agent.git
cd nasdaq-agent
sudo ./deploy.sh
```

The deployment script handles:
- System dependencies installation
- Python environment setup
- Service configuration
- Firewall setup
- Log rotation
- Systemd service creation

### Docker Deployment (Coming Soon)

Docker support is planned for future releases.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_agent_bridge_a2a.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/
```

### Local Development

```bash
# Run with auto-reload
python main.py  # Set DEBUG=true in .env

# Or use uvicorn directly
uvicorn main:main --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Core Endpoints

- `GET /` - API information and available endpoints
- `GET /health` - Health check
- `GET /status` - Detailed system status
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

### Analysis Endpoints

- `POST /api/v1/analyze` - Analyze a stock with natural language query
- `GET /api/v1/agent/info` - Get agent information and capabilities

### A2A Endpoints (when NEST enabled)

- `POST /a2a` - Agent-to-Agent communication endpoint

## Monitoring

### Logs

Application logs are stored in `logs/`:
- `analyses.jsonl` - Stock analysis requests and responses
- `errors.jsonl` - Error logs

### Health Checks

```bash
# Quick health check
./health_check.sh

# Detailed status
curl http://localhost:8000/status
```

### NEST Monitoring

When NEST is enabled, monitor A2A communication:

```bash
# Check NEST status
./scripts/monitor_nest.sh

# View A2A logs
tail -f logs/nest_a2a.log
```

## Troubleshooting

### Common Issues

**Service won't start:**
- Check `ANTHROPIC_API_KEY` is set correctly
- Verify port 8000 is not in use: `lsof -i :8000`
- Check logs: `tail -f logs/errors.jsonl`

**NEST A2A not working:**
- Verify `NEST_ENABLED=true` in `.env`
- Check port 6000 is open in firewall
- Ensure `python-a2a` is installed: `pip show python-a2a`
- Check NEST logs for errors

**Import errors with python-a2a:**
- Ensure you're using python-a2a 0.5.10+
- Verify imports use `run_server` not `serve`
- Reinstall: `pip install --upgrade python-a2a`

### Validation

```bash
# Validate environment configuration
./validate_env.sh .env

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/agent/info
```

## Dependencies

### Core Dependencies

- **FastAPI** - Modern web framework
- **Uvicorn** - ASGI server
- **LangChain** - LLM orchestration
- **Anthropic** - Claude AI integration
- **yfinance** - Market data
- **Pydantic** - Data validation

### Optional Dependencies

- **python-a2a** - NEST A2A framework (requires Python 3.10+)
- **mcp** - Model Context Protocol (requires Python 3.10+)

See `requirements.txt` for complete dependency list.

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

[Add your license here]

## Support

For issues, questions, or contributions:
- Check the [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for deployment issues
- Review logs in `logs/` directory
- Open an issue on GitHub

## Acknowledgments

- Built with [LangChain](https://langchain.com/)
- Powered by [Anthropic Claude](https://www.anthropic.com/)
- Market data from [Yahoo Finance](https://finance.yahoo.com/)
- A2A communication via [NEST Framework](https://github.com/nandaai/python-a2a)
