import subprocess
import sys
import time

args = sys.argv
if len(args) < 1:
    print("Please specify the path to the trainer's artifacts")
    sys.exit(1)

# Tensorboard needs to be killed and restarted in order to open it in a different logdir
subprocess.run("killall -q tensorboard", shell=True)
# run in background and save output on file for debugging
subprocess.run(f"nohup /opt/conda/bin/tensorboard --logdir {args[1]} --bind_all > /tmp/tensorboard.logs 2>&1 &",
               shell=True)
print("Starting Tensorboard...")

# wait few seconds for it to start
time.sleep(6)
print("Ready")
