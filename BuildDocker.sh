#!/usr/bin/env bash
# python3.9 -m venv env
# source env/bin/activate
# pip install numpy casadi
# pip freeze > requirements.txt
docker login -u nathanlazarus
docker build -t nathanlazarus/pythondeforestation:compressing .
docker push nathanlazarus/pythondeforestation:compressing
