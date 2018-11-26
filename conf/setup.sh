
echo 'Creating User'
adduser www
usermod -aG sudo www
su www

echo 'Setting Server Name'
sudo nano /etc/hostname /etc/hosts
echo 'done'

echo 'Updating Ubuntu'
sudo apt update && sudo apt upgrade -y
sudo apt install git -y
echo 'done'

echo 'Updating Python'
sudo apt install python-pip -y
sudo apt install python3.6-dev -y
sudo apt install python3-venv -y
sudo apt install build-essential -y
sudo apt install python3-dev -y
sudo apt install python3-venv -y
echo 'done'

echo 'Downloading Analitico'
cd /home/www
git clone https://gitlab.com/analitico/analitico.git
cd /home/www/analitico
echo 'done'

echo 'Create Virtual Environment'
cd /home/www/analitico
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo 'done'


echo 'Installing Nginx'
sudo apt install nginx -y
systemctl status nginx
echo 'done'

echo 'Applying Configuration'
sudo rm /etc/nginx/nginx.conf
sudo ln -s /home/www/analitico/conf/nginx.conf /etc/nginx/
sudo systemctl restart nginx
echo 'done'

echo 'Configuring Gunicorn'
cd /home/www/analitico/source
python3 manage.py collectstatic
sudo ln -s /home/www/analitico/conf/gunicorn_analitico.service /etc/systemd/system
sudo systemctl start gunicorn_analitico
systemctl status gunicorn_analitico
echo 'done'
