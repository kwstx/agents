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
    def _check_dependencies(module_name: str):
        """
        Checks if the plugin's manifest.yaml declares satisfied dependencies.
        """
        import os
        import yaml
        from importlib.metadata import version, PackageNotFoundError
        from packaging.specifiers import SpecifierSet
        from packaging.version import parse as parse_version

        spec = importlib.util.find_spec(module_name)
        if not spec or not spec.origin:
            return

        # Look for manifest.yaml in the same directory
        plugin_dir = os.path.dirname(spec.origin)
        manifest_path = os.path.join(plugin_dir, "manifest.yaml")

        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r') as f:
                    manifest = yaml.safe_load(f)
                
                dependencies = manifest.get("dependencies", {})
                for pkg_name, version_spec in dependencies.items():
                    try:
                        installed_ver_str = version(pkg_name)
                        installed_ver = parse_version(installed_ver_str)
                        specifiers = SpecifierSet(version_spec)
                        
                        if installed_ver not in specifiers:
                            raise ImportError(
                                f"Dependency Conflict: {module_name} requires {pkg_name}{version_spec}, "
                                f"but installed version is {installed_ver_str}"
                            )
                    except PackageNotFoundError:
                        raise ImportError(f"Missing Dependency: {module_name} requires {pkg_name}, which is not installed.")
                        
            except ImportError:
                raise
            except Exception as e:
                logger.warning(f"Failed to validate manifest for {module_name}: {e}")

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
            # DEPENDENCY VALIDATION
            AgentRegistry._check_dependencies(module_name)

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
