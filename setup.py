from setuptools import setup, find_packages

setup(
    name="agent_forge",
    version="0.2.0",
    description="The Risk Verification Platform for Autonomous Agents",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "typer>=0.9.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "websockets>=11.0",
        "pyyaml>=6.0",
        "rich>=13.0"
    ],
    entry_points={
        "console_scripts": [
            "agent-forge=agent_forge.cli:app",
        ],
    },
    python_requires=">=3.9",
)
