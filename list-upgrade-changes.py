#!/bin/python

import pathlib
import shutil
import signal
import subprocess
import sys


def error_exit(msg):
    print(msg, file=sys.stderr)
    exit(1)


def sigint_handler(sig, frame):
    print("\nExiting per user request.")
    exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigint_handler)
    answer = input("Do you want to sync the pacman database (Y/n)? ")
    if answer == "y" or answer == "":
        try:
            subprocess.chech_call(["pacman", "-Sy"])
        except subprocess.CalledProcessError:
            error_exit("Failed to sync the database")
    elif answer == "n":
        pass
    else:
        error_exit(f"Unexpected answer '{answer}', aborting.")
    upgrades = subprocess.check_output(["pacman", "-Qu"], encoding="utf-8").splitlines()
    for upgrade in upgrades:
        package, curr_version, _, updated_version = upgrade.split(" ")
        print(f"Package {package} will be upgraded from version {curr_version} to {updated_version}\n")
        change_count = input("How many log entries do you want to display? (Default = 1): ")
        if change_count == "":
            change_count = "1"
        else:
            try:
                int(change_count)
            except ValueError:
                error_exit(f"{change_count} is not an integer.")
        if shutil.which("pacolog"):
            pacolog_path = "pacolog"
        else:
            if pathlib.Path("pacolog").is_file():
                pacolog_path = "./pacolog"
            else:
                error_exit("pacolog was not found in the PATH or the current directory.")
        try:
            subprocess.check_call([pacolog_path, "-l", change_count, package])
        except subprocess.CalledProcessError:
            print(f"Failed to call pacolog for the package {package}")
        print()
        input("Press Enter to contiune or Ctrl+C to quit")