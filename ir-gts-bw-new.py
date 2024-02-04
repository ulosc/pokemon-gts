#!/usr/bin/python

# "A script that acts as the GTS, for sending and receiving pokemon between a
# retail cart and a PC. Credit goes to LordLandon and his sendpkm script, as
# well as the description of the GTS protocol from
# http://projectpokemon.org/wiki/GTS_protocol
#
# - Infinite Recursion"
#
# Resurrection of the Infinite Recursion pseudo-GTS script, now with 80% more
# infinite recursion! This is always a work in progress, started by Infinite
# Recursion and LordLandon, with some code borrowed from Pokecheck.org.
# 
# - chickenmatt5
#
# Changes:
#   - Fixed online mode to work post Nintendo server shutdown. (Using pkmnclassic.net DNS server)
#   - Fixed queue based PKM sending.
#   - Made the menu clear the screen after selecting an option for easier readability
#   - Removed all references to Pokecheck.org, that site redirects to a scam/ad site now.
#
# ~ ThyImortalGamer

from src import gtsvar
from src.pokehaxlib import initServ
from src.getpkm import getpkm
from src.sendpkm import sendpkm, multisend, queuesend, customqueuesend
from src.stats import statana
from src.gbatonds import threetofour
from src.util import clear, cleanexit
from platform import system
from sys import argv, exit
from time import sleep
import os

def offlinemenu():
    while True:
        print('\nChoose:')
        print('a - analyze pkm file')
        print('o - continue to online mode')
        print('c - convert .pkm files to newer gens')
        print('q - quit\n')
        print('\nPlease type your option, and press Enter\n')
        choice = input().strip().lower()

        if choice.startswith('a'):
            clear()
            statana()
        elif choice.startswith('o'):
            clear()
            print('\nContinuing to online menu...\n\n')
            break
        elif choice.startswith('c'):
            threetofour()
        elif choice.startswith('q'):
            clear()
            print('Quitting program')
            cleanexit()
        else:
            print('Invalid option, please try again.')
            continue
        clear()
        print('Returning to menu...\n')

def onlinemenu():
    while True:
        print('\nChoose an option:')
        print('s - send pkm file to game')
        print('r - receive Pokemon from game')
        print('m - receive multiple Pokemon from game')
        print('a - analyze pkm file')
        print('q - quit\n')
        print('\nPlease type your option, and press Enter\n')
        option = input().strip().lower()

        if option.startswith('s'):
            clear()
            sendmenu()
        elif option.startswith('r'):
            clear()
            getpkm()
        elif option.startswith('m'):
            clear()
            print('Press ctrl + c to return to main menu')
            while True:
                try: getpkm()
                except KeyboardInterrupt: break
        elif option.startswith('a'):
            clear()
            statana()
        elif option.startswith('q'):
            clear()
            print('Quitting program')
            cleanexit()
        else:
            print('Invalid option, try again')
            continue
        clear()
        print('Returning to main menu...')

def convertmenu():
    while True:
        print('\nChoose a conversion option:')
        print('1 - convert 3rd gen Pokemon file to 4th gen .pkm')
        print('2 - convert 3rd gen Pokemon file to 5th gen .pkm')
        print('3 - convert 4th gen .pkm to 5th gen .pkm')
        print('r - return to main menu')
        print('q - quit')
        number = input().strip().lower()

        if number.startswith('1'): 
            clear()
            threetofour()
        elif number.startswith('2'):
            clear()
            threetofive()
        elif number.startswith('3'):
            clear()
            fourtofive()
        elif number.startswith('r'):
            clear() 
            break
        elif number.startswith('q'):
            clear()
            print('Quitting program')
            cleanexit()
        else:
            print('Invalid option, try again')
            continue
        clear()
        print('Returning to conversion menu...')

def sendmenu():
    while True:
        print('\nChoose an option to send Pokemon:')
        print('o - send one Pokemon to game')
        print('m - choose & send multiple Pokemon to game')
        print('f - send all Pokemon in queue folder')
        print('c - choose folder full of Pokemon to send')
        print('r - return to main menu')
        print('q - quit\n')
        print('\nPlease type your option, and press Enter\n')
        soption = input().strip().lower()

        if soption.startswith('o'):
            clear()
            sendpkm()
        elif soption.startswith('m'):
            clear()
            multisend()
        elif soption.startswith('f'):
            clear()
            queuesend()
        elif soption.startswith('c'):
            clear()
            customqueuesend()
        elif soption.startswith('r'):
            clear()
            break
        elif soption.startswith('q'):
            print('Quitting program')
            cleanexit()
        else:
            print('Invalid option, try again')
            continue
        clear()
        print('Returning to send menu...')


def main():
    s = system()
    if s == 'Darwin' or s == 'Linux':
        if os.getuid() != 0:
            print('Program must be run as superuser. Enter your password below' + \
                    ' if prompted.')
            os.system('sudo python3 ./' + argv[0] + ' root')
            exit(0)

    print("\n", gtsvar.version, "\n")
    if gtsvar.stable == 'no':
        print("===============================================")
        print("EXPERIMENTAL/UNSTABLE VERSION! MIGHT HAVE BUGS!")
        print("===============================================\n")

    offlinemenu()

    initServ()
    sleep(1)

    done = False
    onlinemenu()

if __name__ == "__main__":
    try:
        clear()
        main()
    except KeyboardInterrupt:
        cleanexit()
