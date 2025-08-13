#compdef nw net-worker network-toolkit

_nw_complete() {
  local -a cmds opts values
  local curcontext="$curcontext" state line
  typeset -A opt_args

  _arguments -C \
    '(- : )1:command:->cmds' \
    '(-c --config)'{-c,--config}'[Configuration file or directory]:path:_files -g "*.yml *.yaml" -/' \
    '(-v --verbose)'{-v,--verbose}'[Enable verbose output]' \
    '(-h --help)'{-h,--help}'[Show help]' \
    '(-s --store-results)'{-s,--store-results}'[Store results]' \
    '(-)-results-dir[Results directory]:directory:_files -/' \
    '(-)--raw[Raw output format]:format:(txt json)' \
    '(-i --interactive-auth)'{-i,--interactive-auth}'[Interactive authentication]' \
    '(-p --platform)'{-p,--platform}'[Platform type]:platform:(mikrotik_routeros)' \
    '(-)--port[SSH port]:port:(22 2222 8022)' \
    '(-)--layout[tmux layout]:layout:(tiled even-horizontal even-vertical main-horizontal main-vertical)' \
    '(-)--auth[Authentication mode]:auth:(key-first key password interactive)' \
    '*::args:->args'

  local cfg
  if [[ -n ${opt_args[--config]} ]]; then
    cfg=${opt_args[--config]}
  elif [[ -d config || -f config/config.yml ]]; then
    cfg="config"
  else
    cfg="devices.yml"
  fi

  case $state in
    cmds)
  values=(${(f)"$(nw __complete --for commands 2>/dev/null)"})
      _describe -t commands 'nw commands' values && return
      ;;
    args)
      case $words[2] in
        info)
          values=(${(f)"$(nw __complete --for devices --config \"$cfg\" 2>/dev/null)"})
          _describe -t devices 'devices' values && return ;;
        run)
          if (( CURRENT == 3 )); then
            # Groups first, then devices for better UX, annotate entries
            local -a groups devices annotated
            groups=(${(f)"$(nw __complete --for groups --config \"$cfg\" 2>/dev/null)"})
            devices=(${(f)"$(nw __complete --for devices --config \"$cfg\" 2>/dev/null)"})
            annotated=()
            local g d
            for g in $groups; do annotated+="$g:group"; done
            for d in $devices; do annotated+="$d:device"; done
            values=($annotated)
            _describe -t targets 'targets (groups first)' values && return
          elif (( CURRENT == 4 )); then
            local target=$words[3]
            values=(${(f)"$(nw __complete --for sequences --device \"$target\" --config \"$cfg\" 2>/dev/null)"})
            _describe -t sequences 'sequences' values && return
          fi ;;
        ssh)
          if (( CURRENT == 3 )); then
            local -a groups devices annotated
            groups=(${(f)"$(nw __complete --for groups --config \"$cfg\" 2>/dev/null)"})
            devices=(${(f)"$(nw __complete --for devices --config \"$cfg\" 2>/dev/null)"})
            annotated=()
            local g d
            for g in $groups; do annotated+="$g:group"; done
            for d in $devices; do annotated+="$d:device"; done
            values=($annotated)
            _describe -t targets 'targets (groups first)' values && return
          fi ;;
        upload|download|config-backup|backup|firmware-upgrade|firmware-downgrade|bios-upgrade|diff)
          if (( CURRENT == 3 )); then
            values=(${(f)"$(nw __complete --for devices --config \"$cfg\" 2>/dev/null)"} ${(f)"$(nw __complete --for groups --config \"$cfg\" 2>/dev/null)"})
            _describe -t targets 'targets' values && return
          fi ;;
        list-sequences)
          # options handled by _arguments; nothing positional
          ;;
      esac
      ;;
  esac

  return 0
}

compdef _nw_complete nw net-worker network-toolkit
