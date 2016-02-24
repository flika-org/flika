import os, shutil, subprocess, sys, time

time.sleep(1)
remove = sys.argv[1]
replace_with = sys.argv[2]

os.rename(remove,remove + '-old')
os.rename(replace_with,remove)
shutil.rmtree(remove + '-old')
subprocess.call(['python', 'flika.py'])