#compdef nw networka network-toolkit

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
    '(-o --output-mode)'{-o,--output-mode}'[Output mode]:mode:(default light dark no-color raw)' \
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
          # Offer devices, groups, and sequences for info command
          local -a devices groups sequences annotated
          devices=(${(f)"$(nw __complete --for devices --config \"$cfg\" 2>/dev/null)"})
          groups=(${(f)"$(nw __complete --for groups --config \"$cfg\" 2>/dev/null)"})
          sequences=(${(f)"$(nw __complete --for sequences --config \"$cfg\" 2>/dev/null)"})
          annotated=()
          local d g s
          # Annotate device entries
          for d in $devices; do
            annotated+=("$d:device")
          done
          # Annotate group entries
          for g in $groups; do
            annotated+=("$g:group")
          done
          # Annotate sequence entries
          for s in $sequences; do
            annotated+=("$s:sequence")
          done
          _describe -t targets 'info targets' annotated && return ;;
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
        config)
          if (( CURRENT == 3 )); then
            values=("init:Initialize a network toolkit configuration" "validate:Validate the configuration file")
            _describe -t subcommands 'config subcommands' values && return
          fi ;;
        schema)
          if (( CURRENT == 3 )); then
            values=("update:Update JSON schemas for YAML editor validation" "info:Display information about JSON schema files")
            _describe -t subcommands 'schema subcommands' values && return
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

compdef _nw_complete nw networka network-toolkit
