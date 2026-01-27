import pytest
import sys

if __name__ == "__main__":
    retcode = pytest.main(["-v", "tests/test_order_book_mechanics.py"])
    if retcode == 0:
        print("\nALL TESTS PASSED")
    else:
        print(f"\nTESTS FAILED with code {retcode}")
