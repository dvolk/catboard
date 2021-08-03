# Catboard: a simple task board

- Multiple boards
- Multiple lanes
- Lanes can have different columns
- Responsive layout (works on phones)
- All core functionality works without javascript enabled
- Used in the UK government

## Screenshots

<img src="https://i.imgur.com/A0dzAkZ.png" width=400> 
<img src="https://i.imgur.com/aKLnBfg.png" width=400>

## Installation

    git clone https://gitea.mmmoxford.uk/dvolk/catboard
    cd catboard
    virtualenv env
    pip3 install -r requirements.txt
    flask db upgrade

## Running

    python3 app.py

## Authentication

Catboard doesn't provide any authentication.

If you want to run a publically accessible catboard, you can configure your web server to use basic authentication on the catboard domain.
