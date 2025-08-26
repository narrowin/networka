#!/usr/bin/env bash
# Dynamic Bash completion for nw powered by `nw __complete`.

# Guard for old bash without completion helpers
if ! declare -F _init_completion >/dev/null 2>&1; then
    _init_completion() { return 0; }
fi

_nw() {
    local cur prev words cword
    _init_completion || {
        cur=${COMP_WORDS[COMP_CWORD]}
        prev=${COMP_WORDS[COMP_CWORD-1]}
    }

    cur=${cur:-${COMP_WORDS[COMP_CWORD]}}
    prev=${prev:-${COMP_WORDS[COMP_CWORD-1]}}

    # Helper: find value after an option (e.g. --config)
    _after_opt() {
        local opt="$1"; local i
        for (( i=1; i<${#COMP_WORDS[@]}-1; i++ )); do
            if [[ "${COMP_WORDS[i]}" == "$opt" ]]; then
                echo "${COMP_WORDS[i+1]}"; return 0
            fi
        done
        return 1
    }

    # Resolve config option if provided
    local cfg
    cfg=$(_after_opt --config)
    [[ -z "$cfg" ]] && cfg=$(_after_opt -c)
    if [[ -z "$cfg" ]]; then
        if [[ -d config || -f config/config.yml ]]; then
            cfg="config"
        else
            cfg="devices.yml"
        fi
    fi

    # Try to find nw command - check if available, otherwise try python module
    local nw_cmd=""
    if command -v nw >/dev/null 2>&1; then
        nw_cmd="nw"
    elif command -v python >/dev/null 2>&1; then
        nw_cmd="python -m network_toolkit.cli"
    else
        return 0  # No way to run completion
    fi

    # Dynamic lists via hidden command with fallback
    _nw_list() {
        local what="$1"; shift
        case "$what" in
            commands)
                # Try the completion command first, then fallback to static list
                local result
                result=$($nw_cmd __complete --for commands 2>/dev/null)
                if [[ -n "$result" ]]; then
                    echo "$result"
                else
                    echo "info run upload download backup firmware ssh diff list config schema complete"
                fi
                return ;;
            devices)
                # Try the completion command first, then fallback to parsing config
                local result
                result=$($nw_cmd __complete --for devices --config "$cfg" 2>/dev/null)
                if [[ -n "$result" ]]; then
                    echo "$result"
                else
                    # Fallback: parse devices.yml directly
                    if [[ -f "$cfg/devices.yml" ]]; then
                        grep -E "^  [a-zA-Z0-9_-]+:" "$cfg/devices.yml" 2>/dev/null | sed 's/^  \([^:]*\):.*/\1/' | tr '\n' ' '
                    elif [[ -f "$cfg" && "$cfg" =~ \.ya?ml$ ]]; then
                        grep -E "^  [a-zA-Z0-9_-]+:" "$cfg" 2>/dev/null | sed 's/^  \([^:]*\):.*/\1/' | tr '\n' ' '
                    fi
                fi
                return ;;
            groups)
                # Try the completion command first, then fallback to parsing config
                local result
                result=$($nw_cmd __complete --for groups --config "$cfg" 2>/dev/null)
                if [[ -n "$result" ]]; then
                    echo "$result"
                else
                    # Fallback: parse groups.yml directly
                    if [[ -f "$cfg/groups.yml" ]]; then
                        grep -E "^  [a-zA-Z0-9_-]+:" "$cfg/groups.yml" 2>/dev/null | sed 's/^  \([^:]*\):.*/\1/' | tr '\n' ' '
                    fi
                fi
                return ;;
            sequences)
                local dev="$1"; shift || true
                local result
                if [[ -n "$dev" ]]; then
                    result=$($nw_cmd __complete --for sequences --device "$dev" --config "$cfg" 2>/dev/null)
                else
                    result=$($nw_cmd __complete --for sequences --config "$cfg" 2>/dev/null)
                fi
                if [[ -n "$result" ]]; then
                    echo "$result"
                else
                    # Fallback: basic sequences
                    echo "system_info interface_status backup_config"
                fi
                return ;;
            sequence-groups)
                $nw_cmd __complete --for sequence-groups --config "$cfg" 2>/dev/null; return ;;
            tags)
                $nw_cmd __complete --for tags --config "$cfg" 2>/dev/null; return ;;
        esac
    }

    local cmd
    cmd=${COMP_WORDS[1]}

    # First arg: suggest commands
    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "$(_nw_list commands)" -- "$cur") )
        return 0
    fi

    # File/directory/value options
    case "$prev" in
        --config|-c)
            # complete YAML files and directories
            local files dirs
            files=$(compgen -f -X '!*.yml !*.yaml' -- "$cur")
            dirs=$(compgen -d -- "$cur")
            COMPREPLY=( $files $dirs )
            return 0 ;;
        --output-mode|-o)
            COMPREPLY=( $(compgen -W "default light dark no-color raw" -- "$cur") ); return 0 ;;
        --layout)
            COMPREPLY=( $(compgen -W "tiled even-horizontal even-vertical main-horizontal main-vertical" -- "$cur") ); return 0 ;;
        --results-dir)
            COMPREPLY=( $(compgen -d -- "$cur") ); return 0 ;;
        --raw)
            COMPREPLY=( $(compgen -W "txt json" -- "$cur") ); return 0 ;;
        --platform|-p)
            COMPREPLY=( $(compgen -W "mikrotik_routeros" -- "$cur") ); return 0 ;;
        --port)
            COMPREPLY=( $(compgen -W "22 2222 8022" -- "$cur") ); return 0 ;;
        --auth)
            COMPREPLY=( $(compgen -W "key-first key password interactive" -- "$cur") ); return 0 ;;
    esac

    # Common options per command
    local common_opts="--config -c --verbose -v --help -h"
    local output_opts="--output-mode -o"
    local run_opts="--store-results -s --results-dir --raw --interactive-auth -i --platform -p --port $output_opts $common_opts"
    local upload_opts="--remote-name -r --verify --no-verify --checksum-verify --no-checksum-verify --max-concurrent -j $common_opts"
    local download_opts="--delete-remote --keep-remote --verify --no-verify $common_opts"
    local config_backup_opts="$common_opts"
    local firmware_upgrade_opts="$common_opts"
    local firmware_downgrade_opts="$common_opts"
    local bios_upgrade_opts="$common_opts"
    local list_devices_opts="$output_opts $common_opts"
    local list_groups_opts="$output_opts $common_opts"
    local list_sequences_opts="--vendor --category $output_opts $common_opts"
    local ssh_opts="--config -c --auth --user --password --layout --session-name --window-name --reuse --sync --no-sync --use-sshpass --attach --no-attach --platform -p --port $common_opts"
    local info_opts="--interactive-auth -i $output_opts $common_opts"
    local config_validate_opts="$common_opts"
    local config_init_opts="$common_opts --force"
    local diff_opts="$common_opts"

    # Helper: complete from a list or options
    _opts() { COMPREPLY=( $(compgen -W "$1" -- "$cur") ); }

    case "$cmd" in
        info)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                # Offer devices, groups, and sequences for info command
                local devices groups sequences
                devices=$(_nw_list devices)
                groups=$(_nw_list groups)
                sequences=$(_nw_list sequences)
                _opts "$devices $groups $sequences"
            else
                _opts "$info_opts"
            fi
            ;;
        run)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                # Show groups first, then devices for friendlier targeting
                local groups devices
                groups=$(_nw_list groups)
                devices=$(_nw_list devices)
                _opts "$groups $devices"
            elif [[ ${COMP_CWORD} -eq 3 ]]; then
                local target="${COMP_WORDS[2]}"
                # If target is a device, include vendor/device sequences
                _opts "$(_nw_list sequences "$target")"
            else
                _opts "$run_opts"
            fi
            ;;
        ssh)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                local groups devices
                groups=$(_nw_list groups)
                devices=$(_nw_list devices)
                _opts "$groups $devices"
            else
                if [[ $cur == -* ]]; then _opts "$ssh_opts"; fi
            fi
            ;;
        upload)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                local groups devices
                groups=$(_nw_list groups)
                devices=$(_nw_list devices)
                _opts "$devices $groups"
            elif [[ ${COMP_CWORD} -eq 3 ]]; then
                compopt -o filenames 2>/dev/null || true
                COMPREPLY=( $(compgen -f -- "$cur") )
            else
                _opts "$upload_opts"
            fi
            ;;
        download)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                local groups devices
                groups=$(_nw_list groups)
                devices=$(_nw_list devices)
                _opts "$devices $groups"
            elif [[ ${COMP_CWORD} -eq 4 ]]; then
                # local path argument
                compopt -o filenames 2>/dev/null || true
                COMPREPLY=( $(compgen -d -- "$cur") )
            else
                _opts "$download_opts"
            fi
            ;;
        backup)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                _opts "config comprehensive vendors"
            elif [[ ${COMP_CWORD} -eq 3 && ("${COMP_WORDS[2]}" == "config" || "${COMP_WORDS[2]}" == "comprehensive") ]]; then
                local groups devices
                groups=$(_nw_list groups)
                devices=$(_nw_list devices)
                _opts "$devices $groups"
            else
                _opts "$config_backup_opts"
            fi
            ;;
        firmware)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                _opts "upgrade downgrade bios vendors"
            elif [[ ${COMP_CWORD} -eq 3 && ("${COMP_WORDS[2]}" == "upgrade" || "${COMP_WORDS[2]}" == "downgrade" || "${COMP_WORDS[2]}" == "bios") ]]; then
                local groups devices
                groups=$(_nw_list groups)
                devices=$(_nw_list devices)
                _opts "$devices $groups"
            else
                _opts "$firmware_upgrade_opts"
            fi
            ;;
        diff)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                local groups devices
                groups=$(_nw_list groups)
                devices=$(_nw_list devices)
                _opts "$devices $groups"
            else
                _opts "$diff_opts"
            fi
            ;;
        list)
            # Handle list subcommands
            if [[ ${#COMP_WORDS[@]} -eq 3 ]]; then
                # If we're at position 2 (after "nw list"), suggest subcommands
                COMPREPLY=( $(compgen -W "devices groups sequences supported-types" -- "$cur") )
            elif [[ ${#COMP_WORDS[@]} -gt 3 ]]; then
                # Handle options for specific subcommands
                case "${COMP_WORDS[2]}" in
                    devices)
                        _opts "$list_devices_opts" ;;
                    groups)
                        _opts "$list_groups_opts" ;;
                    sequences)
                        _opts "$list_sequences_opts" ;;
                    supported-types)
                        _opts "$common_opts" ;;
                    *)
                        _opts "$common_opts" ;;
                esac
            fi
            ;;
        config)
            # Handle config subcommands
            if [[ $COMP_CWORD -gt 2 ]]; then
                local config_subcommand="${COMP_WORDS[2]}"
                case "$config_subcommand" in
                    init)
                        _opts "$config_init_opts" ;;
                    validate)
                        _opts "$config_validate_opts" ;;
                    *)
                        _opts "$common_opts" ;;
                esac
            else
                # Complete config subcommands
                COMPREPLY=( $(compgen -W "init validate" -- "$cur") )
            fi
            ;;
        complete)
            # Handle completion command options
            _opts "$common_opts --for --device"
            ;;
        schema)
            # Handle schema subcommands
            if [[ $COMP_CWORD -gt 2 ]]; then
                local schema_subcommand="${COMP_WORDS[2]}"
                case "$schema_subcommand" in
                    update|info)
                        _opts "$common_opts" ;;
                    *)
                        _opts "$common_opts" ;;
                esac
            else
                # Complete schema subcommands
                COMPREPLY=( $(compgen -W "update info" -- "$cur") )
            fi
            ;;
        *)
            # Fallback: suggest common opts
            if [[ $cur == -* ]]; then _opts "$common_opts"; fi ;;
    esac

    return 0
}

# Register the completion function for nw and common aliases
complete -F _nw nw 2>/dev/null || true
complete -F _nw networka 2>/dev/null || true
complete -F _nw network-toolkit 2>/dev/null || true
