# Custom LLM Provider Plugin

An example integration plugin that demonstrates how to connect a custom LLM service to Auto Code and provide MCP tools for agents to use custom language model capabilities.

## Overview

This plugin shows how to integrate a custom LLM provider (OpenAI-compatible API, HuggingFace, custom endpoints, etc.) with Auto Code's agent system. It provides MCP tools that allow agents to use your custom LLM for text completion and chat during builds.

**Note:** This example uses a mock file-based LLM client for demonstration. In a real implementation, you would replace `MockLLMClient` with actual HTTP API calls to your LLM service.

## What It Does

- **Custom LLM Integration**: Connects to a custom LLM service endpoint
- **MCP Tool Creation**: Provides three tools for agents:
  - `custom_llm_complete` - Text completion
  - `custom_llm_chat` - Chat-based interaction
  - `custom_llm_usage` - Usage statistics tracking
- **Configuration Management**: Supports endpoint URL, API key, and model selection
- **Usage Tracking**: Records request history and token usage
- **Build Lifecycle Hooks**: Monitors build start/complete and logs usage stats

## Features Demonstrated

### IntegrationPlugin Capabilities

- `create_mcp_tools()` - Creates custom tools for agents to use
- `on_load()` - Validates configuration on plugin load
- `on_enable()` - Initializes LLM client connection
- `on_disable()` - Cleans up resources
- `on_unload()` - Final cleanup and state persistence

### Build Lifecycle Hooks

- `on_build_start()` - Called when a build starts
- `on_build_complete()` - Called when build finishes, logs LLM usage
- `on_subtask_update()` - Tracks subtask progress

### Configuration

The plugin uses environment variables for configuration:
- `CUSTOM_LLM_ENDPOINT` - LLM API endpoint URL (default: `https://api.example.com/v1`)
- `CUSTOM_LLM_API_KEY` - API authentication key (default: `sk-demo-key`)
- `CUSTOM_LLM_MODEL` - Model identifier (default: `custom-model-v1`)
- `CUSTOM_LLM_DATA_DIR` - Directory for usage data (default: `~/.auto-claude/custom-llm`)

## Installation

### From Directory

1. **Copy the plugin directory**:
   ```bash
   cp -r examples/plugins/custom-llm-provider ~/.auto-claude/plugins/user/
   ```

2. **Configure environment variables** in `apps/backend/.env`:
   ```bash
   CUSTOM_LLM_ENDPOINT=https://api.your-llm-service.com/v1
   CUSTOM_LLM_API_KEY=your-api-key-here
   CUSTOM_LLM_MODEL=your-model-name
   ```

3. **Using the Electron UI**:
   - Open Auto Code desktop app
   - Navigate to **Plugins** (shortcut: `U`)
   - Click **Install Plugin**
   - Select **Directory** as installation source
   - Browse to `examples/plugins/custom-llm-provider`
   - Click **Install**

4. **Enable the plugin**:
   - Find `custom-llm-provider` in the plugins list
   - Click **Enable**

## Usage

Once enabled, agents will have access to three new MCP tools during builds:

### 1. Text Completion

```python
# Agents can use this tool to generate text completions
custom_llm_complete(
    prompt="Explain the singleton pattern in Python",
    max_tokens=150
)
```

Returns:
```json
{
  "text": "Generated completion text...",
  "tokens": 145,
  "model": "custom-model-v1",
  "timestamp": "2024-01-15T10:30:00"
}
```

### 2. Chat Interaction

```python
# Agents can use this for multi-turn conversations
custom_llm_chat(
    messages=[
        {"role": "user", "content": "What is dependency injection?"},
        {"role": "assistant", "content": "Dependency injection is..."},
        {"role": "user", "content": "Can you show an example?"}
    ],
    max_tokens=200
)
```

Returns:
```json
{
  "message": {
    "role": "assistant",
    "content": "Here's an example of dependency injection..."
  },
  "tokens": 180,
  "model": "custom-model-v1",
  "timestamp": "2024-01-15T10:31:00"
}
```

### 3. Usage Statistics

```python
# Check LLM usage during the build
custom_llm_usage()
```

Returns:
```json
{
  "total_requests": 15,
  "total_tokens": 2340,
  "recent_requests": 15
}
```

## Extending for Real LLM Integration

To adapt this plugin for a real LLM service:

### 1. Replace MockLLMClient with Real HTTP Client

```python
import requests

class RealLLMClient:
    def __init__(self, endpoint: str, api_key: str, model: str):
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model

    def complete(self, prompt: str, max_tokens: int = 100) -> dict:
        """Call your LLM API for completion."""
        response = requests.post(
            f"{self.endpoint}/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "prompt": prompt,
                "max_tokens": max_tokens
            }
        )
        response.raise_for_status()
        return response.json()

    def chat(self, messages: list[dict], max_tokens: int = 100) -> dict:
        """Call your LLM API for chat."""
        response = requests.post(
            f"{self.endpoint}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens
            }
        )
        response.raise_for_status()
        return response.json()
```

### 2. Update plugin.py

Replace `MockLLMClient` initialization in `on_enable()`:
```python
def on_enable(self) -> None:
    endpoint = self.get_config_value("CUSTOM_LLM_ENDPOINT")
    api_key = self.get_config_value("CUSTOM_LLM_API_KEY")
    model = self.get_config_value("CUSTOM_LLM_MODEL")

    # Use real client instead of mock
    self.client = RealLLMClient(endpoint, api_key, model)
```

### 3. Add Dependencies

If using `requests`:
```json
{
  "dependencies": ["requests>=2.31.0"]
}
```

### 4. Error Handling

Add proper error handling for API failures:
```python
def complete_text(prompt: str, max_tokens: int = 100) -> dict:
    try:
        result = self.client.complete(prompt, max_tokens=max_tokens)
        return result
    except requests.HTTPError as e:
        logger.error(f"LLM API error: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": "Internal error"}
```

## Supported LLM Providers

This plugin can be adapted for various LLM providers:

- **OpenAI-Compatible APIs**: OpenAI, Azure OpenAI, Together AI, Anyscale
- **Open Source Models**: HuggingFace Inference API, Replicate, vLLM
- **Custom Endpoints**: Self-hosted models (Ollama, LM Studio, LocalAI)
- **Cloud Providers**: AWS Bedrock, Google Vertex AI, Anthropic Claude

## Configuration Examples

### OpenAI-Compatible Endpoint
```bash
CUSTOM_LLM_ENDPOINT=https://api.openai.com/v1
CUSTOM_LLM_API_KEY=sk-your-openai-key
CUSTOM_LLM_MODEL=gpt-4
```

### HuggingFace Inference API
```bash
CUSTOM_LLM_ENDPOINT=https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1
CUSTOM_LLM_API_KEY=hf_your_token_here
CUSTOM_LLM_MODEL=mistralai/Mixtral-8x7B-Instruct-v0.1
```

### Local Ollama Instance
```bash
CUSTOM_LLM_ENDPOINT=http://localhost:11434/api
CUSTOM_LLM_API_KEY=not-required
CUSTOM_LLM_MODEL=llama2
```

## Permissions

This plugin requires the following permissions:

- **network_access**: To make HTTP requests to the LLM API endpoint
- **create_mcp_tools**: To provide MCP tools to agents

## Troubleshooting

### Plugin loads but tools don't work

- Ensure the plugin is **enabled**, not just installed
- Check that environment variables are set correctly
- Verify the LLM endpoint is reachable: `curl $CUSTOM_LLM_ENDPOINT`

### "Client not initialized" warning

- The plugin couldn't connect to the LLM service
- Check your API credentials and endpoint URL
- Look for error messages in the logs

### API authentication errors

- Verify your API key is correct
- Check if the API key has sufficient permissions
- Some providers require special header formats (update the client code)

### Rate limiting or quota errors

- Add retry logic with exponential backoff
- Implement request throttling
- Consider caching responses for identical prompts

## Learn More

- [Integration Plugin Development Guide](../../../guides/plugins/integration-plugins.md)
- [MCP Tools Documentation](../../../docs/mcp-tools.md)
- [Plugin SDK Reference](../../../apps/backend/plugins/sdk/integration.py)
- [Example: OpenAI Integration](https://github.com/OBenner/Auto-Coding/tree/main/examples/integrations/openai)

## License

MIT - See LICENSE file for details
