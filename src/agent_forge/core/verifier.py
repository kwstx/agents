import os
import sys
import yaml
import ast
import importlib.util
from pathlib import Path
from typing import Tuple, List, Dict, Any

class Verifier:
    """
    Validates agent structure, configuration, and constraints.
    """
    
    def __init__(self, agent_path: str):
        self.path = Path(agent_path).absolute()
        self.errors = []
        self.warnings = []

    def verify(self) -> bool:
        """Runs all verification checks."""
        self.errors = []
        self.warnings = []
        
        # 1. Static Analysis
        if not self._check_structure():
            return False
            
        if not self._validate_config():
            return False
            
        if not self._analyze_code():
            return False
            
        # 2. Smoke Test (Safe Run)
        if not self._smoke_test():
            return False
            
        return True

    def _check_structure(self) -> bool:
        """Checks for required files."""
        required_files = ["agent_config.yaml", "my_agent.py"]
        missing = [f for f in required_files if not (self.path / f).exists()]
        
        if missing:
            self.errors.append(f"Missing required files: {', '.join(missing)}")
            return False
        return True

    def _validate_config(self) -> bool:
        """Validates agent_config.yaml structure."""
        try:
            with open(self.path / "agent_config.yaml", "r") as f:
                config = yaml.safe_load(f)
                
            if not isinstance(config, dict):
                self.errors.append("agent_config.yaml must be a dictionary")
                return False
                
            if "agent" not in config:
                self.errors.append("Missing 'agent' section in config")
                return False
                
            required_fields = ["name", "vertical"]
            for field in required_fields:
                if field not in config["agent"]:
                    self.errors.append(f"Missing required field 'agent.{field}'")
                    return False
                    
            return True
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Config validation error: {e}")
            return False

    def _analyze_code(self) -> bool:
        """Static analysis of my_agent.py."""
        try:
            with open(self.path / "my_agent.py", "r") as f:
                tree = ast.parse(f.read())
                
            # Check for class MyAgent
            agent_class = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "MyAgent":
                    agent_class = node
                    break
            
            if not agent_class:
                self.errors.append("my_agent.py must define a class named 'MyAgent'")
                return False
            
            # Check for method process_task or think
            methods = [n.name for n in agent_class.body if isinstance(n, ast.FunctionDef)]
            if "process_task" not in methods and "think" not in methods:
                 self.errors.append("MyAgent must implement 'process_task' or 'think' method")
                 return False
                 
            return True
        except SyntaxError as e:
            self.errors.append(f"Syntax Error in my_agent.py: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Code analysis error: {e}")
            return False

    def _smoke_test(self) -> bool:
        """Attempt to load the module and instantiate the agent class."""
        # Add path to sys.path to allow imports
        sys.path.insert(0, str(self.path))
        
        try:
            spec = importlib.util.spec_from_file_location("my_agent", self.path / "my_agent.py")
            if not spec or not spec.loader:
                self.errors.append("Could not load my_agent module spec")
                return False
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if not hasattr(module, "MyAgent"):
                self.errors.append("my_agent module does not have a 'MyAgent' class")
                return False
                
            # Try instantiation
            try:
                agent = module.MyAgent()
            except Exception as e:
                self.errors.append(f"Failed to instantiate MyAgent: {e}")
                return False
                
            return True
            
        except ImportError as e:
             self.errors.append(f"Import Error: {e}")
             return False
        except Exception as e:
             self.errors.append(f"Smoke test failed: {e}")
             return False
        finally:
            # Cleanup sys.path
            if str(self.path) in sys.path:
                sys.path.remove(str(self.path))

    def get_report(self) -> str:
        """Generate a formatted report string."""
        if not self.errors:
            return "[BOLD GREEN]VERIFICATION PASSED[/BOLD GREEN]"
        
        report = ["[BOLD RED]VERIFICATION FAILED[/BOLD RED]"]
        for err in self.errors:
            report.append(f"- {err}")
        return "\n".join(report)
