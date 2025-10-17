# bugs

- make les output in INFO it's too verbose already

- make sure ipv6 wortks and dns names too for running commands!

- why can i not give a list of deivces to backup like in the run command?

- nw backup router1
  backup up a mikrotik router does not properlyl download the export_compact file created and of course doesn't delete after creation either on the switch - fix that
  mischa@mdx:~/git/narrowin/networka (backup-feature) ✗1 % less /tmp/backups/router1_20251016_150345/export_compact.txt
  mischa@mdx:~/git/narrowin/networka (backup-feature) % cat /tmp/backups/router1_20251016_150345/export_compact.tx
  cat: /tmp/backups/router1_20251016_150345/export_compact.tx: No such file or directory

# To add

- add a summary after creating a backup
- add option to all commands running a remote ssh session to ignore the server ssh key mismatch error and ccontinue
- make output less verbose by not defaulting to INFO output
  is this actually read from ~/.config/networka/config.yaml?
- howto is the config backup path derived?

# To try out

- run networka in gemini-cli interactive shell and see what we can do running in a containerlab
