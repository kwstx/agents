import subprocess

with open("replay_debug_out.txt", "w") as f:
    subprocess.run(["python", "tests/verify_memory_replay.py"], stdout=f, stderr=f, text=True)
