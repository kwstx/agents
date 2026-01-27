import pytest
import sys

if __name__ == "__main__":
    retcode = pytest.main(["-v", "tests/test_risk_enforcement.py"])
    if retcode == 0:
        print("\nALL RISK TESTS PASSED")
    else:
        print(f"\nRISK TESTS FAILED with code {retcode}")
