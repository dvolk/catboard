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

Catboard doesn't provide any authentication.

If you want to run a publically accessible catboard, you can configure your web server to use basic authentication on the catboard domain.

Examples for nginx and caddy 2.0+ follow:

### nginx

Create a `htpasswd` file with the `htpasswd` command.

```
server {
    server_name catboard.example.com;

    listen 443 ssl;
    ssl_certificate /path/to/certs/example.com.cert.pem;
    ssl_certificate_key /path/to/certs/example.com.key.pem;

    location / {
        auth_basic "Restricted Content";
        auth_basic_user_file /etc/nginx/.htpasswd;

        proxy_pass http://127.0.0.1:7777;
        proxy_http_version 1.1;
        proxy_set_header Connection "upgrade";
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### caddy 2.0+

use `caddy hash-password` to create the `PASSWORD_HASH`

```
your_catboard_domain {
  basicauth /* {
    USERNAME PASSWORD_HASH
  }
  reverse_proxy http://127.0.0.1:7777
}

Caddy will set up a certificate automatically from letsencrypt.
```
