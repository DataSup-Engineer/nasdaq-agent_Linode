# NASDAQ Stock Agent - Linode Deployment Guide

Quick guide for deploying the NASDAQ Stock Agent on Linode.

## Prerequisites

- Linode account
- SSH key configured
- Anthropic API key

## Quick Start

### 1. Create Linode Instance

**Recommended Configuration:**
- **Distribution**: Ubuntu 22.04 LTS
- **Plan**: Linode 4GB (Dedicated 4GB RAM, 2 CPU cores)
- **Region**: Choose closest to your users
- **SSH Keys**: Add your public key

**Minimum Requirements:**
- 2 GB RAM (Linode 2GB)
- 2 CPU cores
- 20 GB storage

### 2. Connect to Your Linode

```bash
ssh root@<YOUR_LINODE_IP>
```

### 3. Clone Repository

```bash
cd /root
git clone https://github.com/DataSup-Engineer/nasdaq-agent.git
cd nasdaq-agent
```

### 4. Run Deployment Script

```bash
chmod +x deploy_linode.sh
sudo ./deploy_linode.sh
```

The script will:
- Install Python 3.11 and dependencies
- Create application directory at `/opt/nasdaq-agent`
- Set up system user and permissions
- Configure UFW firewall (ports 22, 8000, 6000)
- Install Python packages
- Set up systemd service
- Configure log rotation

### 5. Configure Environment

```bash
# Create .env file
sudo nano /opt/nasdaq-agent/.env
```

**Minimum configuration:**
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
ANTHROPIC_MODEL=claude-3-haiku-20240307

# Application
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Optional - NEST A2A
NEST_ENABLED=true
NEST_PORT=6000
NEST_PUBLIC_URL=http://<YOUR_LINODE_IP>:6000
```

**Secure the file:**
```bash
sudo chmod 600 /opt/nasdaq-agent/.env
sudo chown nasdaq-agent:nasdaq-agent /opt/nasdaq-agent/.env
```

### 6. Start the Service

```bash
# Start service
sudo systemctl start nasdaq-agent

# Check status
sudo systemctl status nasdaq-agent

# View logs
sudo journalctl -u nasdaq-agent -f
```

### 7. Test the Deployment

```bash
# Health check
curl http://localhost:8000/health

# From your local machine
curl http://<YOUR_LINODE_IP>:8000/health

# Test stock analysis
curl -X POST http://<YOUR_LINODE_IP>:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "What do you think about Apple stock?"}'
```

## Linode Firewall Configuration

The deployment script configures UFW automatically, but you may also want to configure Linode's Cloud Firewall for additional security.

### Linode Cloud Firewall (Optional)

1. Go to Linode Cloud Manager
2. Navigate to "Firewalls"
3. Click "Create Firewall"
4. Add inbound rules:
   - **SSH**: TCP port 22 (your IP only)
   - **HTTP API**: TCP port 8000 (all IPv4/IPv6)
   - **NEST A2A**: TCP port 6000 (all IPv4/IPv6)
5. Attach to your Linode instance

## Updating the Application

```bash
cd /opt/nasdaq-agent
sudo -u nasdaq-agent git pull
sudo ./deploy_linode.sh --update
```

## Monitoring

```bash
# Service status
sudo systemctl status nasdaq-agent

# Real-time logs
sudo journalctl -u nasdaq-agent -f

# Application logs
sudo tail -f /var/log/nasdaq-agent/*.log

# Health check
/opt/nasdaq-agent/health_check.sh
```

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u nasdaq-agent -n 50

# Verify environment
sudo /opt/nasdaq-agent/validate_env.sh /opt/nasdaq-agent/.env

# Check port availability
sudo netstat -tuln | grep 8000
```

### Firewall issues

```bash
# Check UFW status
sudo ufw status numbered

# Allow port manually
sudo ufw allow 8000/tcp
sudo ufw allow 6000/tcp
```

### Cannot connect from external IP

1. Verify UFW allows the ports:
   ```bash
   sudo ufw status
   ```

2. Check if service is listening:
   ```bash
   sudo netstat -tuln | grep -E '8000|6000'
   ```

3. Test from Linode instance first:
   ```bash
   curl http://localhost:8000/health
   ```

4. If Linode Cloud Firewall is enabled, verify rules allow traffic

## Performance Tuning

### Multiple Workers

For production workloads:

```bash
sudo nano /etc/systemd/system/nasdaq-agent.service
```

Update ExecStart:
```
ExecStart=/opt/nasdaq-agent/venv/bin/uvicorn main:main --host 0.0.0.0 --port 8000 --workers 4
```

Reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart nasdaq-agent
```

### Resource Monitoring

```bash
# CPU and memory
htop

# Disk usage
df -h

# Service resources
systemctl status nasdaq-agent
```

## Backup

```bash
# Backup configuration
sudo cp /opt/nasdaq-agent/.env /root/nasdaq-agent-env-backup-$(date +%Y%m%d)

# Backup entire application
sudo tar -czf /root/nasdaq-agent-backup-$(date +%Y%m%d).tar.gz \
  --exclude='/opt/nasdaq-agent/venv' \
  --exclude='/opt/nasdaq-agent/logs' \
  /opt/nasdaq-agent
```

## Security Best Practices

1. **Restrict SSH**: Only allow your IP
   ```bash
   sudo ufw delete allow 22/tcp
   sudo ufw allow from YOUR_IP to any port 22
   ```

2. **Use Linode Cloud Firewall**: Additional layer of protection

3. **Enable automatic updates**:
   ```bash
   sudo apt install unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```

4. **Regular backups**: Use Linode Backups service

5. **Monitor logs**: Check for suspicious activity
   ```bash
   sudo journalctl -u nasdaq-agent --since today
   ```

## Cost Optimization

- **Development**: Linode 2GB ($12/month)
- **Production (Small)**: Linode 4GB ($24/month)
- **Production (Medium)**: Linode 8GB ($48/month)

Use Linode's hourly billing to test before committing.

## Support

- Check logs: `sudo journalctl -u nasdaq-agent -f`
- Health check: `/opt/nasdaq-agent/health_check.sh`
- Validate config: `/opt/nasdaq-agent/validate_env.sh /opt/nasdaq-agent/.env`

## Differences from AWS EC2

- Uses UFW firewall (not firewalld)
- Simpler networking (no VPC/Security Groups complexity)
- Direct root access by default
- Linode Cloud Firewall is optional but recommended
- Generally simpler setup process

## Next Steps

1. Set up domain name and SSL certificate (Let's Encrypt)
2. Configure reverse proxy (nginx) for HTTPS
3. Enable Linode Backups
4. Set up monitoring and alerts
5. Configure log aggregation

For detailed information, see the main [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).
