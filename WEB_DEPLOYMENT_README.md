# AIF Web Application Deployment Guide

This guide explains how to deploy the AIF web application to an Ubuntu server alongside your existing Telegram bot.

## Prerequisites

- Ubuntu server (18.04 or later)
- Existing Telegram bot deployment
- Root or sudo access
- Domain name or static IP (optional but recommended)

## Project Structure

```
/home/ubuntu/AIF/
├── web_app.py              # Main Flask application
├── aif.py                  # Telegram bot
├── requirements.txt        # Python dependencies
├── production.db           # SQLite database (shared with bot)
├── start_web.sh           # Web app startup script
├── stop_web.sh            # Web app shutdown script
├── status_web.sh          # Web app status monitoring
├── aif-web.service        # Systemd service file
├── aif-web.nginx          # Nginx configuration
├── deploy_web.sh          # Deployment script
└── web/                   # Modular web components
    ├── __init__.py
    ├── models.py
    ├── utils.py
    ├── templates.py
    └── translations.py
```

## Quick Deployment

1. **Upload files to server:**
   ```bash
   # Copy all files to /home/ubuntu/AIF/
   scp -r . ubuntu@your-server:/home/ubuntu/AIF/
   ```

2. **Run deployment script:**
   ```bash
   ssh ubuntu@your-server
   cd /home/ubuntu/AIF
   chmod +x deploy_web.sh
   ./deploy_web.sh
   ```

3. **Configure domain (optional):**
   - Edit `/etc/nginx/sites-available/aif-web`
   - Replace `your-domain.com` with your actual domain
   - Restart nginx: `sudo systemctl restart nginx`

4. **Setup SSL (recommended):**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

## Manual Deployment Steps

If you prefer manual deployment:

### 1. Install Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib
```

### 2. Setup Python Environment
```bash
cd /home/ubuntu/AIF
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Systemd Service
```bash
sudo cp aif-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable aif-web
sudo systemctl start aif-web
```

### 4. Configure Nginx
```bash
sudo cp aif-web.nginx /etc/nginx/sites-available/aif-web
sudo ln -s /etc/nginx/sites-available/aif-web /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Service Management

### Web Application
```bash
# Start
sudo systemctl start aif-web
# or
./start_web.sh

# Stop
sudo systemctl stop aif-web
# or
./stop_web.sh

# Status
sudo systemctl status aif-web
# or
./status_web.sh

# Restart
sudo systemctl restart aif-web

# Logs
sudo journalctl -u aif-web -f
```

### Nginx
```bash
sudo systemctl status nginx
sudo systemctl restart nginx
sudo tail -f /var/log/nginx/aif-web.access.log
```

## Database

The web application uses the same SQLite database (`production.db`) as your Telegram bot. No database migration is needed.

## Security Considerations

1. **Firewall:** Ensure only necessary ports are open (22, 80, 443)
2. **SSL:** Always use HTTPS in production
3. **User Permissions:** Services run as `ubuntu` user, not root
4. **File Permissions:** Restrict access to sensitive files

## Troubleshooting

### Web app not starting
```bash
# Check logs
sudo journalctl -u aif-web -f

# Check if port 8080 is free
sudo netstat -tlnp | grep 8080

# Test manually
cd /home/ubuntu/AIF
source venv/bin/activate
python web_app.py
```

### Nginx errors
```bash
# Test configuration
sudo nginx -t

# Check logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/aif-web.error.log
```

### Permission issues
```bash
# Fix ownership
sudo chown -R ubuntu:ubuntu /home/ubuntu/AIF

# Fix permissions
sudo chmod +x /home/ubuntu/AIF/*.sh
```

## Backup Strategy

```bash
# Database backup
cp production.db production.db.backup.$(date +%Y%m%d_%H%M%S)

# Full backup
tar -czf backup-$(date +%Y%m%d_%H%M%S).tar.gz /home/ubuntu/AIF
```

## Monitoring

- Web app status: `./status_web.sh`
- System resources: `htop` or `top`
- Logs: `sudo journalctl -u aif-web -f`

## Access URLs

- Web Application: `http://your-domain.com` or `http://server-ip`
- Telegram Bot: Already configured and running

## Support

If you encounter issues:
1. Check the logs using the commands above
2. Verify all files are properly uploaded
3. Ensure the database file exists and is accessible
4. Check that the virtual environment is properly activated