# Use the official Nginx image.
# https://hub.docker.com/_/nginx/
FROM nginx
RUN mkdir -p /root/certs/
# Copy configuration
COPY nginx.conf /etc/nginx/nginx.conf
# Copy ssl domain certificates
COPY analitico.ai.crt /root/certs/analitico.ai.crt
COPY analitico.ai.key /root/certs/analitico.ai.key