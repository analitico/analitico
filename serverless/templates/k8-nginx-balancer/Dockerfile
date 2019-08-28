# Use the official Nginx image.
# https://hub.docker.com/_/nginx/
FROM nginx

RUN adduser www --disabled-login --disabled-password  --gecos "" && adduser www root

# Startup script
COPY startup.sh /bin/analitico-startup
RUN chmod +x /bin/analitico-startup

##
## Nginx
##

RUN mkdir -p /root/certs/
# Copy configuration
COPY nginx.conf /etc/nginx/nginx.conf
# Copy ssl domain certificates
COPY analitico.ai.crt /root/certs/analitico.ai.crt
COPY analitico.ai.key /root/certs/analitico.ai.key

# Install common packages
RUN apt-get update && apt-get install -y bash nano cifs-utils util-linux

##
## Netdata for load balancer monitoring
##

RUN apt-get install -y curl uuid-dev zlib1g zlib1g-dev gcc git autoconf-archive autogen netcat libmnl-dev libuv1-dev liblz4-dev libssl-dev libjudy-dev python make pkg-config

COPY netdata-kickstart.sh .
RUN chmod +x netdata-kickstart.sh
# Install from the official script
RUN bash -c ./netdata-kickstart.sh --non-interactive
# Cleanup
RUN rm ./netdata-kickstart.sh
RUN apt-get remove -y curl uuid-dev zlib1g-dev gcc git autoconf-archive autogen libmnl-dev libuv1-dev liblz4-dev libssl-dev libjudy-dev make

# To collect nginx, weblog (nginx, gunicorn): 
COPY netdata/collectors/python.d/nginx.conf /etc/netdata/python.d/
COPY netdata/collectors/python.d/web_log.conf /etc/netdata/python.d/
COPY netdata/collectors/python.d/httpcheck.conf /etc/netdata/python.d/

# Enable notifications
COPY netdata/health_alarm_notify.conf /etc/netdata/

# Default log files redirect to the stdout and prevent nginx to write 
RUN rm /var/log/nginx/access.log /var/log/nginx/error.log 
RUN adduser netdata www

##
## Mount for Website's static files
##

# Save credentials for mounting
COPY analitico-env.sh ./analitico-env.sh
RUN chmod +x ./analitico-env.sh

# Mount on boot
RUN mkdir /mnt/analitico-drive
RUN /bin/bash -c 'source ./analitico-env.sh && echo "//$ANALITICO_DRIVE_WEBSITE_USERNAME.your-storagebox.de/$ANALITICO_DRIVE_WEBSITE_USERNAME /mnt/analitico-drive cifs ro,file_mode=0660,dir_mode=0770,user=$ANALITICO_DRIVE_WEBSITE_USERNAME,pass=$ANALITICO_DRIVE_WEBSITE_PASSWORD 0 0" >> /etc/fstab'

RUN rm ./analitico-env.sh