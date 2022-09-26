#!/usr/bin/env bash
flask db upgrade
python3 app.py --host 0.0.0.0
