#!/bin/bash

fswatch -e ".*" -i "\\.py$" . | while read; do
    echo "File changed, running deploy"
    python main.py --deploy
done