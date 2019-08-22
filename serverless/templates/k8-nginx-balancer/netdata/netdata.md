
# netdata

Real-time performance monitoring, done right!   
https://my-netdata.io  
https://github.com/netdata/netdata   

To install netdata on local server:  
`bash <(curl -Ss https://my-netdata.io/kickstart.sh)`   

To collect nginx, weblog (nginx, gunicorn), mysql data: 
`sudo cp collectors/python.d/nginx.conf /etc/netdata/python.d/`  
`sudo cp collectors/python.d/web_log.conf /etc/netdata/python.d/`
`sudo cp collectors/python.d/mysql.conf /etc/netdata/python.d/`
`sudo cp collectors/python.d/httpcheck.conf /etc/netdata/python.d/`

Enable notifications:
`sudo cp health_alarm_notify.conf /etc/netdata/`

Restart service:   
`sudo systemctl restart netdata`

Debug problems:
`tail -f error.log | grep keyword`

## Tutorials

Netdata Documentation
https://docs.netdata.cloud/

How to Monitor Nginx using Netdata
https://www.howtoforge.com/tutorial/how-to-monitor-nginx-using-netdata-on-ubuntu-1604/

## MySQL

https://github.com/netdata/netdata/tree/master/collectors/python.d.plugin/mysql
https://github.com/PyMySQL/mysqlclient-python

You may need to install the Python and MySQL development headers and libraries like so:
`sudo apt-get install python-dev default-libmysqlclient-dev`
`sudo apt-get install python-mysqldb`

To create read only user for netdata on mysql:
`grant select on analitico.* to 'netdata'@'%' identified by 'rfgTyh56weER';`

## Collectors

nginx    
https://github.com/netdata/netdata/tree/master/collectors/python.d.plugin/nginx   

mysql   
https://www.tecmint.com/monitor-mysql-mariadb-using-netdata-on-centos-7/

web_log
https://github.com/netdata/netdata/tree/master/collectors/python.d.plugin/web_log

http check   
https://github.com/netdata/netdata/tree/master/collectors/python.d.plugin/httpcheck   

## Notifications

Enabling Telegram notifications   
https://docs.netdata.cloud/health/notifications/telegram/   

