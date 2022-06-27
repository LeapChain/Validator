# Project Setup

Follow the steps below to set up the project on your environment. If you run into any problems, feel free to leave a 
GitHub Issue or reach out to any of our communities above.

## Ubuntu setup guide

### Key Generation ~

Before deploying server, run this script to generate all keys that will be needed later for configuration.

https://gist.github.com/mrbusysky/a8963ab01cdf76c7c1cf03210eec8f50

### Install Dependencies ~
Update and install packages:
```
sudo add-apt-repository universe
sudo apt -y update && sudo apt -y upgrade
sudo apt -y install build-essential libpq-dev nginx postgresql postgresql-contrib python3-pip redis-server
```
If it don't stop getting warnings like below, just restart your node.
```
Running kernel seems to be up-to-date.
No services need to be restarted.
No containers need to be restarted.
No user sessions are running outdated binaries.
No VM guests are running outdated hypervisor (qemu) binaries on this host.
```

### Firewall ~
Enable firewall:
```
sudo ufw app list
sudo ufw allow 'Nginx Full' && sudo ufw allow OpenSSH && sudo ufw enable
```
Verify that firewall is active and nginx is running:
```
sudo ufw status && systemctl status nginx
```
You should now be able to visit your server's public IP address and see the welcome page.
Create a new user:
```
sudo adduser deploy
```
Fill the form and set a password

Allow this user to use sudo:
```
sudo visudo
```
Add following line into the opened file:
```
deploy ALL=(ALL) NOPASSWD:ALL
```
Switch to that new user:
```
su - deploy
```
### Project Setup ~

Update /var/www/ permissions:
```
sudo chmod go+w /var/www
```
Clone project to server and install dependencies:
```
git clone https://github.com/LeapChain/Validator.git /var/www/Validator
cd /var/www/Validator/
sudo pip3 install -r requirements/production.txt
```
### NGINX ~

Create NGINX configuration:
```
sudo rm /etc/nginx/sites-available/default
sudo nano /etc/nginx/sites-available/default
```
Paste in the following and save:
```
upstream django {
    server 127.0.0.1:8001;
}

server {
    listen 80 default_server;
    server_name localhost;
    charset utf-8;
    client_max_body_size 75M;

    location /media {
        alias /var/www/Validator/media;
    }

    location /static {
        alias /var/www/Validator/static;
    }

    # Send all non-media requests to the Django server
    location / {
        proxy_pass http://django;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_redirect off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $server_name;
    }

}
```
Test configuration:
```
sudo nginx -t
```
### Redis ~

Since we are running Ubuntu, which uses the systemd init system, change this to systemd:
```
sudo nano /etc/redis/redis.conf
```
Update the following line in the configuration and save file:
```
# Note: these supervision methods only signal "process is ready."
#       They do not enable continuous liveness pings back to your supervisor.
supervised systemd
```
Restart the Redis service to reflect the changes you made to the configuration file:
```
sudo systemctl restart redis.service
```
Check status to make sure Redis is running correctly:
```
sudo systemctl status redis
```
### Gateway Interface (daphne)  ~

Create script to run daphne:
```
sudo nano /usr/local/bin/start_api.sh
```
Paste in the following and save:
```
#!/bin/bash

cd /var/www/Validator
daphne -p 8001 config.asgi:application
```
Update permissions for the shell script:
```
sudo chmod a+x /usr/local/bin/start_api.sh
```
### Celery ~

Create a file to contain our environment variables:
```
cd /etc/
sudo mkdir validator
sudo mkdir /var/log/celery
sudo chown deploy /var/log/celery
sudo nano /etc/validator/environment
```
```
DJANGO_APPLICATION_ENVIRONMENT=production
NETWORK_SIGNING_KEY=YOUR_NID_SIGNING_KEY
SECRET_KEY=YOUR_SECRET_KEY
```
Create celery env config:
```
sudo nano /etc/validator/celery.conf
```
```
CELERYD_NODES="w1 w2 w3"
CELERY_BIN="/usr/local/bin/celery"
CELERY_APP="config.settings"
CELERYD_MULTI="multi"
CELERYD_OPTS="--time-limit=1800 -Q:w1 celery -c:w1 2 -Q:w2 block_queue -P:w2 solo -Q:w3 confirmation_block_queue -P:w3 solo"
CELERYD_PID_FILE="/var/log/celery/%n.pid"
CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
CELERYD_LOG_LEVEL="DEBUG"
DJANGO_APPLICATION_ENVIRONMENT=production
NETWORK_SIGNING_KEY=YOUR_NID_SIGNING_KEY
SECRET_KEY=YOUR_SECRET_KEY
```
Create service:
```
sudo nano /etc/systemd/system/api.service
```
```
[Unit]
Description = Service to run Django API
After = network.target

[Service]
EnvironmentFile = /etc/validator/environment
User = deploy
ExecStart = /usr/local/bin/start_api.sh

[Install]
WantedBy = multi-user.target
```
Update permissions for file:
```
sudo chmod a+x /etc/systemd/system/api.service
```
Create service for celery:
```
sudo nano /etc/systemd/system/celery.service
```
```
[Unit]
Description=Validator Celery Service
After=network.target

[Service]
Type=forking
User=deploy
EnvironmentFile=/etc/validator/celery.conf
WorkingDirectory=/var/www/Validator
ExecStart=/bin/sh -c '${CELERY_BIN} multi start ${CELERYD_NODES} \
  -A ${CELERY_APP} --pidfile=${CELERYD_PID_FILE} \
  --logfile=${CELERYD_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}'
ExecStop=/bin/sh -c '${CELERY_BIN} multi stopwait ${CELERYD_NODES} \
  --pidfile=${CELERYD_PID_FILE}'
ExecReload=/bin/sh -c '${CELERY_BIN} multi restart ${CELERYD_NODES} \
  -A ${CELERY_APP} --pidfile=${CELERYD_PID_FILE} \
  --logfile=${CELERYD_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}'

[Install]
WantedBy=multi-user.target
```
Reload systemd and enable both services:
```
sudo systemctl daemon-reload && sudo systemctl enable api && sudo systemctl enable celery
```
Verify it is enabled:
```
ls /etc/systemd/system/multi-user.target.wants/
```
### System Services ~
Start API service, restart NGINX, and verify services are active:
```
sudo systemctl start api && sudo systemctl start celery && sudo systemctl restart nginx
```
Check the status of the services:
```
sudo systemctl status api celery nginx redis
```
### Static Files and Application Configuration  ~
Set environment variable:
```
nano ~/.profile
```
```
export DJANGO_APPLICATION_ENVIRONMENT="production"
export NETWORK_SIGNING_KEY="YOUR_NID_SIGNING_KEY"
export SECRET_KEY="YOUR_SECRET_KEY"
```
Log out and log back in:
```
logout
su - deploy
printenv
```
### Initialize database:  ~
```
# Create a new user (or more precisely, a role)
sudo -u postgres createuser --interactive

Enter name of role to add: leapchain
Shall the new role be a superuser? (y/n) y

# Create new database
sudo -u postgres createdb leapchain

# Set a password for the user
sudo -u postgres psql template1
ALTER USER leapchain PASSWORD 'yourpassword';

# Exit prompt
\q
```
Edit file with your password:
```
cd /var/www/Validator/

nano config/settings/base.py
```
Populate database:
```
python3 manage.py makemigrations && python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py collectstatic
```
Initialize validator node:
```
python3 manage.py initialize_validator
```
Or Initialize Confirmation node:
```
python3 manage.py set_primary_validator
```
![setup](https://i.gyazo.com/7066c2d47f5e2578674729f3c5078f43.png)
```
Network standardized type of node (PRIMARY_VALIDATOR or CONFIRMATION_VALIDATOR)
```
Verify everything is working correctly by visiting:
```
http://[IP_ADDRESS]/config
```
Troubleshooting
Check the status of the services:
```
sudo systemctl status api celery nginx redis
```
View the logs:
```
sudo journalctl -u api.service
sudo journalctl -u celery.service
sudo journalctl -u nginx.service
```
----

## Windows (without Docker)

This guide targets a unix environment however it is possible to perform this setup on Windows by installing Cygwin 
[here](https://cygwin.com/install.html).

When installing Cygwin ensure you add the following packages in the setup wizard choosing the most up-to-date version for each:

* python3
* python3-devel
* pip3
* gcc-core
* libffi-devel
* make
* python38-wheel
* libintl-devel
  
Once installed use Cygwin for all your command-line operations.

*This is because one of the dependencies, uWSGI, does not provide Windows support directly.*

## Steps (without Docker)

Set required environment variables:
```
# Valid values are development, local, postgres_local, production, or staging
export DJANGO_APPLICATION_ENVIRONMENT='local'

# 64 character signing key used to authenticate network requests
export NETWORK_SIGNING_KEY='6f812a35643b55a77f71c3b722504fbc5918e83ec72965f7fd33865ed0be8f81'

# A string with random chars
export SECRET_KEY='some random string'
```

Install Redis:
```
brew install redis
```

Create a virtual environment with Python 3.6 or higher.

Install required packages:
```
pip3 install -r requirements/local.txt
```

To initialize the project:
```
python3 manage.py migrate
python3 manage.py initialize_test_primary_validator -ip [IP ADDRESS]
```

## Local Development (without Docker)

Run Redis:
```
redis-server
```

Run Celery (run each as a separate process):
```
celery -A config.settings worker -l debug
celery -A config.settings worker -l debug --queue block_queue --pool solo
celery -A config.settings worker -l debug --queue confirmation_block_queue --pool solo
```

To monitor Celery tasks:
```
celery flower -A config.settings --address=127.0.0.1 --port=5555
```

## Developers

To watch log files:
```shell
tail -f logs/warning.log -n 10
```

To run all tests in parallel:
```shell
pytest -n auto
```

When adding a package, add to `requirements/base.in` and then :
```shell
bash scripts/compile_requirements.sh
```

To generate documentation:
```shell
cd docs
make html
```

## License

LeapChain is [MIT licensed](http://opensource.org/licenses/MIT).
