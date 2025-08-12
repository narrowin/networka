# fish completion for netkit using dynamic __complete endpoint

function __netkit_complete
    set -l what $argv[1]
    set -l cfg
    for idx in (seq 1 (count (commandline -opc)))
        set -l tkn (commandline -opc | sed -n "${idx}p")
        if test $tkn = "--config" -o $tkn = "-c"
            set cfg (commandline -opc | sed -n "$(math $idx + 1)p")
            break
        end
    end
    if test -z "$cfg"
        if test -d config -o -f config/config.yml
            set cfg config
        else
            set cfg devices.yml
        end
    end

    switch $what
        case commands
            netkit __complete --for commands 2>/dev/null
        case devices
            netkit __complete --for devices --config "$cfg" 2>/dev/null
        case groups
            netkit __complete --for groups --config "$cfg" 2>/dev/null
        case sequences
            set -l dev $argv[2]
            if test -n "$dev"
                netkit __complete --for sequences --device "$dev" --config "$cfg" 2>/dev/null
            else
                netkit __complete --for sequences --config "$cfg" 2>/dev/null
            end
        case sequence-groups
            netkit __complete --for sequence-groups --config "$cfg" 2>/dev/null
        case tags
            netkit __complete --for tags --config "$cfg" 2>/dev/null
    end
end

complete -c netkit -f -a '(__netkit_complete commands)'

# Common options
complete -c netkit -s c -l config -r -d 'Configuration file or directory'
complete -c netkit -s v -l verbose -d 'Verbose'
complete -c netkit -s h -l help -d 'Help'
complete -c netkit -s i -l interactive-auth -d 'Interactive authentication'
complete -c netkit -s p -l platform -x -a 'mikrotik_routeros' -d 'Platform type'
complete -c netkit -l port -x -a '22 2222 8022' -d 'SSH port'

# Subcommands
complete -c netkit -n '__fish_use_subcommand' -a 'info' -d 'Show device info'
complete -c netkit -n '__fish_use_subcommand' -a 'run' -d 'Run command/sequence'
complete -c netkit -n '__fish_use_subcommand' -a 'upload' -d 'Upload file'
complete -c netkit -n '__fish_use_subcommand' -a 'download' -d 'Download file'
complete -c netkit -n '__fish_use_subcommand' -a 'config-backup' -d 'Backup config'
complete -c netkit -n '__fish_use_subcommand' -a 'backup' -d 'Backup config (alias)'
complete -c netkit -n '__fish_use_subcommand' -a 'firmware-upgrade' -d 'Firmware upgrade'
complete -c netkit -n '__fish_use_subcommand' -a 'firmware-downgrade' -d 'Firmware downgrade'
complete -c netkit -n '__fish_use_subcommand' -a 'bios-upgrade' -d 'RouterBOARD (BIOS) upgrade'
complete -c netkit -n '__fish_use_subcommand' -a 'ssh' -d 'SSH to devices via tmux'
complete -c netkit -n '__fish_use_subcommand' -a 'diff' -d 'Compare configurations'
complete -c netkit -n '__fish_use_subcommand' -a 'list-devices' -d 'List devices'
complete -c netkit -n '__fish_use_subcommand' -a 'list-groups' -d 'List groups'
complete -c netkit -n '__fish_use_subcommand' -a 'list-sequences' -d 'List sequences'
complete -c netkit -n '__fish_use_subcommand' -a 'config-validate' -d 'Validate config'

# Positional completions
complete -c netkit -n '__fish_seen_subcommand_from info' -a '(__netkit_complete devices)'
complete -c netkit -n '__fish_seen_subcommand_from run; and test (count (commandline -opc)) -eq 2' -a '(__netkit_complete groups)' -d 'Group'
complete -c netkit -n '__fish_seen_subcommand_from run; and test (count (commandline -opc)) -eq 2' -a '(__netkit_complete devices)' -d 'Device'
complete -c netkit -n '__fish_seen_subcommand_from run; and test (count (commandline -opc)) -eq 3' -a '(__netkit_complete sequences (commandline -opc | sed -n "2p"))'
# ssh target completion
complete -c netkit -n '__fish_seen_subcommand_from ssh; and test (count (commandline -opc)) -eq 2' -a '(__netkit_complete groups)' -d 'Group'
complete -c netkit -n '__fish_seen_subcommand_from ssh; and test (count (commandline -opc)) -eq 2' -a '(__netkit_complete devices)' -d 'Device'
# Command-specific options
complete -c netkit -n '__fish_seen_subcommand_from run' -l raw -x -a 'txt json' -d 'Raw output format'
complete -c netkit -n '__fish_seen_subcommand_from run' -s s -l store-results -d 'Store results'
complete -c netkit -n '__fish_seen_subcommand_from run' -l results-dir -r -d 'Results directory'
complete -c netkit -n '__fish_seen_subcommand_from ssh' -l layout -x -a 'tiled even-horizontal even-vertical main-horizontal main-vertical' -d 'tmux layout'
complete -c netkit -n '__fish_seen_subcommand_from ssh' -l auth -x -a 'key-first key password interactive' -d 'Authentication mode'
complete -c netkit -n '__fish_seen_subcommand_from ssh' -l user -d 'Username override'
complete -c netkit -n '__fish_seen_subcommand_from ssh' -l password -d 'Password override'
complete -c netkit -n '__fish_seen_subcommand_from ssh' -l session-name -d 'Custom session name'
complete -c netkit -n '__fish_seen_subcommand_from ssh' -l window-name -d 'Custom window name'
complete -c netkit -n '__fish_seen_subcommand_from ssh' -l reuse -d 'Reuse existing session'
complete -c netkit -n '__fish_seen_subcommand_from ssh' -l sync -d 'Enable synchronize-panes'
complete -c netkit -n '__fish_seen_subcommand_from ssh' -l no-sync -d 'Disable synchronize-panes'
complete -c netkit -n '__fish_seen_subcommand_from ssh' -l use-sshpass -d 'Use sshpass'
complete -c netkit -n '__fish_seen_subcommand_from ssh' -l attach -d 'Attach after creating'
complete -c netkit -n '__fish_seen_subcommand_from ssh' -l no-attach -d 'Do not attach'
complete -c netkit -n '__fish_seen_subcommand_from upload; and test (count (commandline -opc)) -eq 2' -a '(__netkit_complete devices) (__netkit_complete groups)'
complete -c netkit -n '__fish_seen_subcommand_from download; and test (count (commandline -opc)) -eq 2' -a '(__netkit_complete devices) (__netkit_complete groups)'
complete -c netkit -n '__fish_seen_subcommand_from config-backup backup; and test (count (commandline -opc)) -eq 2' -a '(__netkit_complete devices) (__netkit_complete groups)'
complete -c netkit -n '__fish_seen_subcommand_from firmware-upgrade; and test (count (commandline -opc)) -eq 2' -a '(__netkit_complete devices) (__netkit_complete groups)'
complete -c netkit -n '__fish_seen_subcommand_from firmware-downgrade; and test (count (commandline -opc)) -eq 2' -a '(__netkit_complete devices) (__netkit_complete groups)'
complete -c netkit -n '__fish_seen_subcommand_from bios-upgrade; and test (count (commandline -opc)) -eq 2' -a '(__netkit_complete devices) (__netkit_complete groups)'
complete -c netkit -n '__fish_seen_subcommand_from diff; and test (count (commandline -opc)) -eq 2' -a '(__netkit_complete devices) (__netkit_complete groups)'
