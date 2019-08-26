# Use the official Nginx image.
# https://hub.docker.com/_/nginx/
FROM nginx

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
RUN bash -c ./netdata-kickstart.sh --non-interactive

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
## Mount for Website app's static files
##

# Save credentials for mounting
RUN /bin/bash -c './analitico-env.sh && echo "username=${ANALITICO_DRIVE_WEBSITE_USERNAME}\npassword=${ANALITICO_DRIVE_WEBSITE_PASSWORD}" > /etc/analitico-drive-credentials.txt'
# Mount on boot
RUN echo "//${ANALITICO_DRIVE_WEBSITE_USERNAME}.your-storagebox.de/${ANALITICO_DRIVE_WEBSITE_USERNAME} /mnt/analitico-drive cifs r,iocharset=utf8,credentials=/etc/analitico-drive-credentials.txt,uid=33,gid=33,file_mode=0660,dir_mode=0770 0 0" >> /etc/fstab
