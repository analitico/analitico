
## Commands

### Git

Drop all changes:   
`git reset --hard`

### Files

List directory contents:   
`ls -l`

Sync local directory with remote directory on server:
`

Create symbolic link:   
`ln -s src dst`

Live tail of log file:   
`tail -f file`

### Processes

Kill all python processes:   
`sudo pkill python`

### Services

Restart gunicorn:   
`sudo systemctl restart gunicorn_service`

Restart nginx:   
`sudo systemctl restart nginx`

See status:   
`service status all`

### Network

See who is using port 8000:   
`lsof -i :8000`

