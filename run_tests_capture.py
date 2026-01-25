import unittest
import sys
import os

# Redirect stderr to stdout
sys.stderr = sys.stdout

def run_tests():
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_dynamic_loading.py')
    
    with open('test_full_output.txt', 'w') as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        result = runner.run(suite)
        
    print("Tests finished. Output written to test_full_output.txt")

if __name__ == '__main__':
    run_tests()
