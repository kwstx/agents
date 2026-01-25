# Developer Guide: Creating a New Agent

This guide outlines the steps to create and register a new agent in the Agent Forge system.

## Prerequisites
- Python 3.9+
- Access to the `agent_forge_mvp` codebase.

## Step 1: Create Your Plugin Directory
Create a folder for your agent (e.g., `my_plugins/my_agent`).
Ensure it has an `__init__.py`.

## Step 2: Define Dependencies (Optional but Recommended)
Create a `manifest.yaml` in your plugin directory to declare dependencies.
```yaml
dependencies:
  requests: ">=2.25.0"
  numpy: ">=1.18.0"
```

## Step 3: Implement the Agent Class
Create a python file (e.g., `custom_agent.py`).
Inherit from `agents.base_agent.BaseAgent` and implement `process_task`.

```python
from agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    async def process_task(self, task):
        # Your custom logic here
        self.logger.info(f"Processing: {task}")
        return {"status": "success", "data": "Processed"}
```

## Step 4: Register and Load
Use the `AgentRegistry` to load your agent dynamically.

```python
from agents.agent_registry import AgentRegistry

# Load the class (not instance)
agent_cls = AgentRegistry.load_agent("my_plugins.my_agent.custom_agent", "CustomAgent")

# Instantiate
agent = agent_cls(agent_id="my_custom_bot", message_bus=bus)
```

## Checklist
- [ ] Inherits from `BaseAgent`.
- [ ] Implements `process_task`.
- [ ] `manifest.yaml` (if needed) matches installed packages.
- [ ] No dangerous imports (`os`, `sys`, `subprocess`).
