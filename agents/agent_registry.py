import importlib
import importlib.util
import ast
import logging
import logging
from typing import Type
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class AgentRegistry:
    @staticmethod
    def load_agent(module_name: str, class_name: str) -> Type[BaseAgent]:
        """
        Dynamically loads an agent class from a given module.

        Args:
            module_name (str): The name of the module (e.g., 'agents.finance_agent').
            class_name (str): The name of the class (e.g., 'FinanceAgent').

        Returns:
            Type[BaseAgent]: The loaded agent class.
        """
        try:
            # SECURITY CHECK: Inspect source before importing
            spec = importlib.util.find_spec(module_name)
            if spec and spec.origin:
                with open(spec.origin, 'r') as f:
                    tree = ast.parse(f.read())
                
                # Blocklist: strictly forbid system access
                DANGEROUS_IMPORTS = {'os', 'sys', 'subprocess', 'shutil'}
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.split('.')[0] in DANGEROUS_IMPORTS:
                                raise ImportError(f"Security Alert: Agent imports illegal module '{alias.name}'")
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.module.split('.')[0] in DANGEROUS_IMPORTS:
                            raise ImportError(f"Security Alert: Agent imports from illegal module '{node.module}'")
            
            module = importlib.import_module(module_name)
            agent_class = getattr(module, class_name)
            if not issubclass(agent_class, BaseAgent):
                 logger.warning(f"{class_name} in {module_name} is not a subclass of BaseAgent.")
            
            # STRICT VALIDATION: Ensure class is concrete (all abstract methods implemented)
            if getattr(agent_class, "__abstractmethods__", set()):
                 missing = ", ".join(agent_class.__abstractmethods__)
                 raise TypeError(f"Agent {class_name} is abstract. Missing methods: {missing}")

            # Check if process_task is implemented OR legacy perform exists
            # Since BaseAgent now has a concrete process_task, we check if the subclass overrides it
            # OR if it provides 'perform'.
            has_process = (agent_class.process_task != BaseAgent.process_task)
            has_perform = hasattr(agent_class, 'perform')
            
            if not (has_process or has_perform):
                raise TypeError(f"Agent {class_name} must implement 'process_task' (preferred) or 'perform' (legacy).")
            
            return agent_class
        except ImportError as e:
            logger.error(f"Failed to import module {module_name}: {e}")
            raise
        except AttributeError as e:
            logger.error(f"Failed to find class {class_name} in module {module_name}: {e}")
            raise
