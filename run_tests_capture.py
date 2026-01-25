import subprocess
import sys

print("Running tests...")
result = subprocess.run(
    ["python", "-m", "pytest", "-v", "tests/test_query_capabilities.py", "tests/test_memory_performance.py"],
    capture_output=True,
    text=True
)

with open("test_full_output.txt", "w", encoding="utf-8") as f:
    f.write(result.stdout)
    f.write("\nSTDERR:\n")
    f.write(result.stderr)
    f.write(f"\nExit Code: {result.returncode}")

print(f"Done. Exit Code: {result.returncode}")
