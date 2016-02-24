import os, shutil, subprocess, sys, time
try:
	time.sleep(2)
	remove = sys.argv[1]
	replace_with = sys.argv[2]

	os.rename(remove,remove + '-old')
	os.rename(replace_with,remove)
	#shutil.rmtree(remove + '-old')
	subprocess.call(['python', 'flika.py'])
except Exception as e:
	print(e)
input('Error')