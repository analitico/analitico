
# Analitico Server Setup & Utils

The website and API run as a Django application. Djiango does not include a web server. Gunicorn acts as a webserver for Django but cannot be exposed to the outer web as it is easily prey to denial of service attacks and is not optimized for static assets, etc. Nginx is used at load balancer, to serve static assets and as a reverse proxy to gunicorn. Both nginx and gunicorn are installed as systemd services which are monitored and automatically booted as needed. Therefore the final architecture is:   

`outer web -> nginx > gunicorn -> django -> application code`


## Server Initialization

The website, along with nginx and gunicorn's deamon runs as 'www' user in 'www' group.

Create user for nginx, gunicorn, etc (see credentials for pwds):   
`adduser www`

Give user sudo access (TODO may not be necessary):  
`usermod -aG sudo www`

Switch to www user:   
`su www`

Change server name:
`sudo gedit /etc/hostname /etc/hosts`

## Server Updates, Upgrades

Update list of available packages, upgrade packages:
`sudo apt update && sudo apt upgrade -y`

Install python3 add ons:  
`sudo apt install python-pip -y`   
`sudo apt install python3.6-dev -y`   
`sudo apt install python3-venv -y`   
`sudo apt install build-essential`
`sudo apt install python3-dev -y`   


## Download and Install Analitico

Clone git repo:   
`cd /home/www`  
`git clone https://gitlab.com/analitico/analitico.git`  
`cd analitico`  

Create python virtual environment:   
`python3 -m venv venv`  

Activate virtual environment:   
`source venv/bin/activate`  

Update packages in virtual env:  
`pip install -r requirements.txt`  

run analitico on port 8000 using django dev server:  
`python3 source/manage.py runserver 0.0.0.0:8000`  


## Nginx Setup

Nginx serves the site's static assets and acts as reverse proxy for django/gunicorn.

Install nginx:   
`sudo apt install nginx`    

Check nginx status:   
`systemctl status nginx`   

Production site home:  
`/home/www/analitico/source`]

Nginx home:  
`/etc/nginx/`

Analitico's nginx conf is symlinked:  
`sudo rm /etc/nginx/nginx.conf`  
`/etc/nginx/nginx.conf`  
`sudo ln -s /home/www/analitico/conf/nginx.conf /etc/nginx/`  

Nginx logs:  
`/var/log/nginx/error.log`  
`tail /var/log/nginx/error.log`

Restarting nginx:
`sudo /etc/init.d/nginx restart`
`sudo systemctl restart nginx`

## Gunicorn

Start gunicorn from the command line (listening to unix socket):  
`cd /home/www/analitico/source/`
`gunicorn website.wsgi -b unix:/tmp/gunicorn.sock`

Install analitico/gunicorn as a service:  
`sudo ln -s /home/www/analitico/conf/gunicorn_analitico.service /etc/systemd/system`  

Start the service:  
`sudo systemctl start gunicorn_analitico`  
 
Check if service is running:  
`systemctl status gunicorn_analitico`  

If configuration changes:
`sudo systemctl daemon-reload`


## MySQL

Create a user with a password  
`GRANT ALL PRIVILEGES ON *.* TO 'analitico'@'localhost' IDENTIFIED BY 'password';`

Make server available from remote hosts:   
`cd /etc/mysql/mysql.conf.d`  
`sudo nano mysqld.cnf`  

Comment out line that binds to 127.0.0.1, see:    
https://stackoverflow.com/questions/14779104/how-to-allow-remote-connection-to-mysql


## Tutorials

Deploying Gunicorn   
https://docs.gunicorn.org/en/latest/deploy.html   

Django and Nginx Tutorial   
https://uwsgi.readthedocs.io/en/latest/tutorials/Django_and_nginx.html

quello in inglese scarso ma semplice
https://tutos.readthedocs.io/en/latest/source/ndg.html

## Alternatives

Setting up Django and your web server with uWSGI and nginx   
https://uwsgi-docs.readthedocs.io/en/latest/tutorials/Django_and_nginx.html

uWSGI Options  
https://uwsgi-docs.readthedocs.io/en/latest/Options.html  

uWSGI configuration help  
https://stackoverflow.com/questions/27196776/uwsgi-upstart-on-amazon-linux  

Install and try uwsgi  
`pip install https://projects.unbit.it/downloads/uwsgi-lts.tar.gz`  
`pip install uwsgi`  
`cd source`  
`uwsgi --http :8000 --module website.wsgi`  
