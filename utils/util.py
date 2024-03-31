import subprocess, platform
from time import sleep

def clear():
    if platform.system()=="Windows":
        subprocess.Popen("cls", shell=True).communicate()
    else: #Linux and Mac
        print("\033c")

def cleanexit():
    clear()
    print("Goodbye...")
    sleep(0.5)
    clear()
    exit()