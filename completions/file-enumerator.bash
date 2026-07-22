_file_enumerator_completion() {
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    case "$prev" in
        --format)
            COMPREPLY=( $(compgen -W 'txt csv both' -- "$cur") )
            return 0
            ;;
        --txt-path-mode)
            COMPREPLY=( $(compgen -W 'full relative' -- "$cur") )
            return 0
            ;;
        -o|--output)
            COMPREPLY=( $(compgen -f -- "$cur") )
            return 0
            ;;
        --output-dir)
            COMPREPLY=( $(compgen -d -- "$cur") )
            return 0
            ;;
        --include-filetype|--include-ext|--exclude-filetype|--exclude-ext)
            return 0
            ;;
        --include-filename|--include-name|--exclude-filename|--exclude-name|--include-foldername|--include-folder|--exclude-foldername|--exclude-folder|--basename)
            return 0
            ;;
    esac

    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W '
            --include-filetype --include-ext
            --exclude-filetype --exclude-ext
            --include-filename --include-name
            --exclude-filename --exclude-name
            --include-foldername --include-folder
            --exclude-foldername --exclude-folder
            -o --output --format --output-dir --basename --txt-path-mode
            --zip --zip-only --exclude-archives --no-archives
            --follow-links --case-sensitive --quiet
            --version --help
        ' -- "$cur") )
    else
        COMPREPLY=( $(compgen -d -- "$cur") )
    fi
}

complete -F _file_enumerator_completion file-enumerator
