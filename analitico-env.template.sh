#!/bin/bash

# Sets the environment variables required by analitico server
# This file is not committed in the main repository but is installed
# and run in development and production with different settings
#
# Apply environment to shell using:
# source analitico-env.sh
#
# Apply environment variables automatically by adding them to:
# ~/.bash_login

echo "analitico.ai: setting environment variables"

# SECURITY WARNING: don't run with debug turned on in production!
export ANALITICO_DEBUG="False"

# Django secret key
export ANALITICO_SECRET_KEY="xxx"

# MySQL configuration
export ANALITICO_MYSQL_HOST="xxx"
export ANALITICO_MYSQL_NAME="xxx"
export ANALITICO_MYSQL_USER="xxx"
export ANALITICO_MYSQL_PASSWORD="xxx"

# Google Cloud Storage private keys (note: using $ to handle escape chars in secret)
export ANALITICO_GCS_KEY="xxx@xxx.com"
export ANALITICO_GCS_SECRET=$"-----BEGIN PRIVATE KEY-----\nxxx\n-----END PRIVATE KEY-----\n"
export ANALITICO_GCS_PROJECT="xxx"

# Example of SendGrid configuration for sending emails
export ANALITICO_EMAIL_HOST="smtp.sendgrid.net"
export ANALITICO_EMAIL_HOST_USER = 'xxx'
export ANALITICO_EMAIL_HOST_PASSWORD = 'xxx'
