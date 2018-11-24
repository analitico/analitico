

nginx home:
`/etc/nginx/`
`/etc/nginx/sites-enabled/`

site home:
`/home/www/analitico/source`

symlink analitico's gunicorn configuration to nginx directory:
`sudo ln -s /home/www/analitico/conf/nginx.conf /etc/nginx/`



starts gunicorn from command line listening to unix socket for nginx connections:
cd source
gunicorn website.wsgi -b unix:/tmp/gunicorn.sock

Restart nginx:
`sudo /etc/init.d/nginx restart`


Deploying Gunicorn   
We strongly recommend to use Gunicorn behind a proxy server.   
https://docs.gunicorn.org/en/latest/deploy.html   


