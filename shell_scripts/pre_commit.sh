#!/usr/bin/env sh
echo "##########################"
echo "Running Tests"
echo "##########################"
poetry run pytest
echo "##########################"
echo "Running isort"
echo "##########################"
poetry run isort --settings-path pyproject.toml app/. tests/.
echo "##########################"
echo "Running black"
echo "##########################"
poetry run black app/. tests/.
echo "##########################"
