# Catboard: a simple task board

- Multiple boards
- Multiple lanes
- Lanes can have different columns
- Responsive layout (works on phones)
- All core functionality works without javascript enabled
- Easy database export to/import from json
- Use sqlite3, mysql or postgresql databases
- Deploy with systemd, docker or kubernetes

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

## Linux deployment

### Setup

By default catboard uses sqlite3 (`./app.db`).

If you would like to use a different database, set the `CATBOARD_SQLALCHEMY_DATABASE_URI` environment variable.

```
sudo apt install python3 python3-pip
git clone https://github.com/dvolk/catboard
cd catboard
virtualenv env
source env/bin/activate
pip3 install -r requirements.txt
flask db upgrade
```

### Run directly

```
python3 app.py
```

### Run with systemd

```
cp catboard.service ~/.config/systemd/user/catboard.service
```

Change the paths in the service file to whereever you've downloaded catboard:

```
vi ~/.config/systemd/user/catboard.service
```

Start the catboard service:

```
systemctl daemon-reload --user
systemctl start catboard
```

## Docker deployment

see `docker-compose.yml`.

The docker deployment uses postgresql.

Works in docker swarm mode too.

## Kubernetes deployment

see `kubernetes/`.

The kubernetes deployment uses mysql 8.

## Authentication

To add users, use cli.py:

```
python3 cli.py add-user username password
```

## Other CLI commands

Commands provided by cli.py are:

```
list-users  # list users
list-boards  # list boards
add-user  # add a user
remove-user  # remove (delete) a user
set-password  # set a user's password
user-add-board  # add a board to a user
user-remove-board  # remove a board from a user
```
