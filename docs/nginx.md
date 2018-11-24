
Nginx installed in:
/etc/nginx

Site repo installed in:
/var/www/analitico


##
## Setup
##

Django and Nginx Tutorial   
https://uwsgi.readthedocs.io/en/latest/tutorials/Django_and_nginx.html

Add analitico to nginx configurations:  
`sudo ln -s /var/www/analitico/source/analitico_nginx.conf /etc/nginx/sites-enabled/`  

Restart nginx:  
`sudo /etc/init.d/nginx restart`  


##
## uWSGI
##

uWSGI Options  
https://uwsgi-docs.readthedocs.io/en/latest/Options.html  

uWSGI configuration help  
https://stackoverflow.com/questions/27196776/uwsgi-upstart-on-amazon-linux  

##
## General
##

What is www-data user?  
https://askubuntu.com/questions/873839/what-is-the-www-data-user  


