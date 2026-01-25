import importlib
import logging
from typing import Type
from .base_env import BaseEnvironment

logger = logging.getLogger(__name__)

class EnvironmentRegistry:
    @staticmethod
    def load_environment(module_name: str, class_name: str) -> Type[BaseEnvironment]:
        """
        Dynamically loads an environment class from a given module.

        Args:
            module_name (str): The name of the module (e.g., 'environments.robotics_sim').
            class_name (str): The name of the class (e.g., 'RoboticsSim').

        Returns:
            Type[BaseEnvironment]: The loaded environment class.
        """
        try:
            module = importlib.import_module(module_name)
            env_class = getattr(module, class_name)
            if not issubclass(env_class, BaseEnvironment):
                logger.warning(f"{class_name} in {module_name} is not a subclass of BaseEnvironment.")
            
            # STRICT VALIDATION: Ensure class is concrete
            if getattr(env_class, "__abstractmethods__", set()):
                missing = ", ".join(env_class.__abstractmethods__)
                raise TypeError(f"Environment {class_name} is abstract. Missing methods: {missing}")
            
            required_methods = ['reset', 'step']
            for method in required_methods:
                if not hasattr(env_class, method):
                    raise TypeError(f"Environment {class_name} missing required method: {method}")
                    
            return env_class
        except ImportError as e:
            logger.error(f"Failed to import module {module_name}: {e}")
            raise
        except AttributeError as e:
            logger.error(f"Failed to find class {class_name} in module {module_name}: {e}")
            raise
