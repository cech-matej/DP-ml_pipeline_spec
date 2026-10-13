#!/bin/sh

ENV_DIR=".venv"

PYTHON_BIN="python3"

show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  -c, --create         Create environment if it does not exist"
    echo "  -r, --recreate       Recreate environment from scratch"
    echo "  -d, --delete         Delete environment"
    echo "  -i, --install        Installs the missing dependencies"
    echo "  -h, --help           Show this help message"
}

safe_return() {
    return "$1" 2>/dev/null || exit "$1"
}

install_project() {
    if [ -f "pyproject.toml" ]; then
        echo "Installing project from pyproject.toml..."
        pip install -e . || safe_return 1
    else
        echo "No pyproject.toml found, skipping install."
    fi
}

create_env() {
    echo "Creating virtual environment..."
    "$PYTHON_BIN" -m venv "$ENV_DIR" || safe_return 1

    echo "Activating environment..."
    . "$ENV_DIR/bin/activate" || safe_return 1

    echo "Upgrading pip..."
    pip install --upgrade pip || safe_return 1

    install_project

    echo "Environment ready."
}

recreate_env() {
    if [ -d "$ENV_DIR" ]; then
        echo "Removing existing environment..."
        rm -rf "$ENV_DIR" || safe_return 1
    fi
    create_env
}

delete_env() {
    if [ -d "$ENV_DIR" ]; then
        echo "Deleting environment..."
        rm -rf "$ENV_DIR" || safe_return 1
        echo "Environment deleted."
    else
        echo "Environment does not exist."
    fi
}

activate_env() {
    if [ ! -d "$ENV_DIR" ]; then
        echo "Environment does not exist. Create it first."
        safe_return 1
    fi

    echo "Activating environment..."
    . "$ENV_DIR/bin/activate" || safe_return 1
}

case "$1" in
    -c|--create)
        if [ $# -ne 1 ]; then
            echo "Option $1 does not accept additional arguments."
            safe_return 1
        fi

        if [ -d "$ENV_DIR" ]; then
            echo "Environment already exists. Doing nothing."
        else
            create_env
        fi
        ;;
    -r|--recreate)
        if [ $# -ne 1 ]; then
            echo "Option $1 does not accept additional arguments."
            safe_return 1
        fi
        recreate_env
        ;;
    -d|--delete)
        if [ $# -ne 1 ]; then
            echo "Option $1 does not accept additional arguments."
            safe_return 1
        fi
        delete_env
        ;;
    -i|--install)
        if [ $# -ne 1 ]; then
            echo "Option $1 does not accept additional arguments."
            safe_return 1
        fi
        activate_env
        install_project
        ;;
    -h|--help)
        show_help
        ;;
    *)
        echo "Unknown option: $1"
        show_help
        safe_return 1
        ;;
esac
