# Catboard: a simple task board

- Multiple boards
- Multiple lanes
- Lanes can have different columns
- Responsive layout (works on phones)
- All core functionality works without javascript enabled
- Used in the UK government

## Screenshots

<table>
    <tr>
        <th>Board index</th>
        <th>Board view</th>
    </tr>
    <tr>
        <td><img src="https://i.imgur.com/ISJfIsC.png"></td>
        <td><img src="https://i.imgur.com/A0dzAkZ.png"></td>
    </tr>
    <tr>
        <th>Board edit</th>
        <th>Issue view</th>
    </tr>
    <tr>
        <td><img src="https://i.imgur.com/NlYPuc5.png"></td>
        <td><img src="https://i.imgur.com/aKLnBfg.png"></td>
    </tr>
</table>

## Installation

    git clone https://gitea.mmmoxford.uk/dvolk/catboard
    cd catboard
    virtualenv env
    source env/bin/activate
    pip3 install -r requirements.txt
    flask db upgrade

## Running

    python3 app.py

## Authentication

Catboard doesn't provide any authentication.

If you want to run a publically accessible catboard, you can configure your web server to use basic authentication on the catboard domain.
