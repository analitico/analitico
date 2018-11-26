
echo 'Create User'
adduser www
usermod -aG sudo www
su www

echo 'Set Server Name'
sudo nano /etc/hostname /etc/hosts

echo 'Update Ubuntu'
sudo apt update && sudo apt upgrade -y
sudo apt install git -y

echo 'Update Python'
sudo apt install python-pip -y
sudo apt install python3.6-dev -y
sudo apt install python3-venv -y
sudo apt install build-essential -y
sudo apt install python3-dev -y
sudo apt install python3-venv -y

echo 'Download Analitico'
cd /home/www
git clone https://gitlab.com/analitico/analitico.git
cd /home/www/analitico

echo 'Create Virtual Environment'
cd /home/www/analitico
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo 'Install Nginx'
sudo apt install nginx -y
systemctl status nginx

echo 'Apply Configuration'
sudo rm /etc/nginx/nginx.conf
sudo ln -s /home/www/analitico/conf/nginx.conf /etc/nginx/
sudo systemctl restart nginx

echo 'Configure Gunicorn'
cd /home/www/analitico/source
python3 manage.py collectstatic
sudo ln -s /home/www/analitico/conf/gunicorn_analitico.service /etc/systemd/system
sudo systemctl start gunicorn_analitico
systemctl status gunicorn_analitico
