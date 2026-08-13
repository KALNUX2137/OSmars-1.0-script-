# OSmars-1.0-script-
OSmars 1.0 is an operating system written in Python. My current plan is to add the Linux kernel and get my system to boot, because I want it to be an independent operating system with Debian integrated into it, which will allow it to run .deb packages. The operating system is currently in Polish, so you may have trouble understanding some things. I guarantee that the next version will be in English. It also includes a GUI written in PySide6. In the next update, I’ll make sure the server runs 24/7, but I can’t promise that the server itself will be up and running in the next update. For now, I can make it available so you can test the server and system over LAN.

TO BE CLEAR! The code may look AI-generated, but I had issues with some functions and used AI to work through everything together and keep the code organized so I wouldn’t get lost.

The correct way to use it is to launch OSmars_recovery first, as it starts the GUI and communicates with it. The recovery system is essentially a terminal with its own built-in terminal, which can be used in case the bin directory gets corrupted or the GUI fails to start.
<img width="475" height="244" alt="obraz" src="https://github.com/user-attachments/assets/52012b13-e8ce-4252-a7e8-94071563f197" />

OSmars GUI Selector is kind of like GRUB. It lets you exit the system or enter recovery mode.

The two GUI applications, gui1.py and Kocmos.py, make up the actual desktop environment. The GUI Selector simply displays whatever is located in OSmars PC/boot/desktop, where the graphical environments are stored.

I currently have two GUIs because I’ve only been testing gui1 for now, and I don’t plan to release it anytime soon because I want to create more than one GUI.
<recovery>:~[17:05]$ help

OSmars Recovery — available commands:

  help, ?              - show this help
  clear, cls           - clear the screen
  ls, dir [-l] [-a]    - list files
  cd <dir>             - change directory
  pwd                  - show current directory
  cat <file>           - display a file
  mkdir <dir>          - create a directory
  touch <file>         - create a file
  rm <file>            - remove a file/directory
  rmdir <dir>          - remove an empty directory
  cp <src> <dst>       - copy
  mv <src> <dst>       - move
  nano / edit <file>   - editor (nano-like)
  find <pattern>       - search for files
  tree                 - directory tree
  info <file>          - file information
  history              - command history
  alias [name=cmd]     - aliases
  config [key] [val]   - configuration

  lsblk                - list disks/block devices
  df                   - disk space
  free                 - RAM usage
  uname [-a]           - system information
  whoami / id / hostname / date / uptime / env / echo / ps

  run / boot <file.py> - run a Python script
  bootsys / boot system - GUI Selector
  status               - Recovery + boot/transaction status
  exit, quit           - exit

  from mars install <pkg>       - download from repo (mars/system/bin)
  from mars uninstall <pkg>     - remove a package (apps/bin/ver)
  from mars update [pkg]        - check versions and update
  marsinstall / marsuninstall / marsupdate
  sync                          - apply boot/instructions
  rollback                      - restore snapshot
  auto-sync [on|off|status]     - auto-sync after downloading
  pacman -S <pkg>               - local install

Boot:
  install → Downloads + instructions → sync (if auto-sync on)
  update  → compares ver/*.json with the server API

Repo: config mars_repo_url

<recovery>:~[17:05]$

These are all the commands currently built into the terminal. Some of them may have bugs or may not work exactly as intended, such as nano. I originally had a different idea for how nano should work, but I decided not to continue developing it, so it was left as it is.

For clarity, if you run OSmars on Windows, don't expect commands such as lsblk to work.

Here's also an example of what installing an application from my repository (website) looks like:
<recovery>:~[17:12]$ from mars install hello
Searching for: hello.mars  (http://myurl/mars/hello.mars)
Found: hello.mars
Downloading → Downloads/hello.mars
✅ Downloaded 'hello.mars' (779 B) to files/Downloads/
📦 .mars saved in Downloads. Open it from Desktop/Downloads or right-click → Install.
<recovery>:~[17:32]$ sync

═══ OSmars sync (boot transaction) ═══
No pending instructions in /boot.
<recovery>:~[17:32]$

You can also update the system. The installer places the update files in /boot, and during the next boot, OSmars installs them where they need to go.

Now, let's move on to Kocmos, which looks like this:
<img width="1920" height="1080" alt="obraz" src="https://github.com/user-attachments/assets/5b8a8649-9adc-4ea5-8e21-ba94fa9bb73e" />
It doesn't look the best, but it includes most of the features. (Sorry, I forgot to add Paint — that will be included in the next update. Also, don't pay attention to the small icons, okay?)

You can browse through files and do a lot of other things, but it would take way too long to explain everything, so I'll just show it in the screenshots.
<img width="1920" height="1080" alt="obraz" src="https://github.com/user-attachments/assets/d7534a91-f27e-472b-9bd6-1e0116e84dd9" />

<img width="446" height="775" alt="obraz" src="https://github.com/user-attachments/assets/37b6ddc5-5335-461b-aa40-6900b9021646" />

<img width="1920" height="1080" alt="obraz" src="https://github.com/user-attachments/assets/4a838148-74c5-4b46-a31d-1d9738090525" />
<img width="1920" height="1080" alt="obraz" src="https://github.com/user-attachments/assets/727f7c34-10ea-4cc4-a0af-f94ad8221cca" />
<img width="1920" height="1080" alt="obraz" src="https://github.com/user-attachments/assets/d1e5d58c-27f6-419a-8752-a573053c0d54" />
<img width="1920" height="1080" alt="obraz" src="https://github.com/user-attachments/assets/e86d9195-27cf-4f3f-934d-aa5aa6b1d805" />
<img width="1920" height="1080" alt="obraz" src="https://github.com/user-attachments/assets/d0240911-a8b6-43d3-8796-3bc9e37b835e" />




