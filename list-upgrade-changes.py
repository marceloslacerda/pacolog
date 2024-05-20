#!/bin/python

import pathlib
import requests
import shlex
import shutil
import signal
import subprocess
import sys

from lxml import html, etree


session = requests.Session()


def error_exit(msg):
    print(msg, file=sys.stderr)
    exit(1)


def sigint_handler(sig, frame):
    print("\nExiting per user request.")
    exit(0)


def get_repository_type(package_name):
    try:
        return subprocess.check_output(
            shlex.split(f"pacman -Spdd --print-format %r {package_name}"),
            encoding="utf-8",
            stderr=subprocess.STDOUT
            ).strip()
    except subprocess.CalledProcessError as err:
        if "target not found" in err.output:
            return "aur"


def get_upgrades():
    lines = subprocess.check_output(["pacman", "-Qu"], encoding="utf-8").splitlines()
    for line in lines:
        package_name, current_version, _, updated_version = line.split(" ")
        repository_type = get_repository_type(package_name)
        if repository_type != 'aur':
            base_url = 'https://gitlab.archlinux.org'
            repository_url = f'{base_url}/archlinux/packaging/packages/{package_name}' 
            commits_url = f'{repository_url}/-/commits/main?ref_type=heads'
        else:
            base_url = 'https://aur.archlinux.org'
            repository_url = f'https://aur.archlinux.org/{package_name}'
            commits_url = None
        
        yield {
            "package": package_name,
            "current_version": current_version,
            "updated_version": updated_version,
            "repository_type": repository_type,
            "commits_url": commits_url,
            "base_url": base_url
        }


def get_commit_data(commit_div):
    elem = commit_div.cssselect('a.commit-row-message')[0]
    message = elem.text
    commit_url = elem.get("href")
    timestring = commit_div.cssselect('time')[0].get("title")
    commiter = commit_div.cssselect("a.commit-author-link")[0].text
    try:
        tag = commit_div.cssselect("div.commit-actions > span > a")[0].text
    except IndexError:
        tag = None
    return tag, message, commiter, timestring, commit_url


def print_commits_since_last_update(upgrade):
    # Sadly gitlab doesn't seem to like me getting a project commits using the api (even when they are public)
    # So I have to scrap it from the html
    response = session.get(upgrade["commits_url"])
    response.raise_for_status()
    tree = html.fromstring(response.content)
    commits = tree.cssselect('div.commit-detail')
    print("Commits since the last version:\n")
    some_commit_printed = False
    for commit in commits:
        tag, message, commiter, timestring, commit_url = get_commit_data(commit)
        if tag is None or upgrade["updated_version"] in tag:
            print(f"({commiter}) {timestring} Message:  {message}")
            print(f"Link: {upgrade["base_url"]}/{commit_url}")
            print()
            some_commit_printed = True
        else:
            if not some_commit_printed:
                print(f"Only commits older than {upgrade["current_version"]} were found")
                print(f"Looking inside {upgrade["commits_url"]}")
            break
    if not commits:
        page = response.content.decode()
        if "You need to sign in or sign up before continuing." in page:
            print(f"Gitlab is demanding a sign-on to access:\n{upgrade['commits_url']}")
        else:
            print(f"No commits found for {upgrade['commits_url']}. This is probably an error.")
            print(page)



def print_upgrades():
    for upgrade in get_upgrades():
        if upgrade["repository_type"] == "aur":
            print(f"{upgrade['package']} is an aur package. Those are not supported for this script.")
            print(f"To look for changes to that package see: {upgrade['repository_url']}\n")
            continue
        print(f"Package {upgrade['package']} will be upgraded from version {upgrade['current_version']} to {upgrade['updated_version']}\n")
        print_commits_since_last_update(upgrade)
        print()
        input("Press Enter to contiune or Ctrl+C to quit")
        print("\n\n")


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
    
    print_upgrades()