# FootyhubAWS — EC2 Deployment Guide

Full step-by-step guide. For a summary see the main [README.md](../README.md).

---

## Prerequisites

- AWS account
- EC2 t3.micro, Ubuntu 22.04 LTS
- Key pair `.pem` file downloaded and saved
- Security group inbound rules: SSH (22), HTTP (80), Custom TCP (8000)
- SQS queue created (`footyhub-articles`)
- IAM role attached to EC2 with SQS read/write permissions

---

## 1. SSH into the instance

```powershell
# Windows PowerShell
ssh -i "C:\path\to\your-key.pem" ubuntu@<ec2-public-ip>
```

---

## 2. Install system dependencies

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv postgresql nginx git
```

---

## 3. Set up PostgreSQL

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE footyhub;
CREATE USER footyhub WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE footyhub TO footyhub;
\q
```

Grant schema permissions:
```bash
sudo -u postgres psql -d footyhub
```
```sql
GRANT ALL ON SCHEMA public TO footyhub;
\q
```

---

## 4. Clone the repo and install Python dependencies

```bash
git clone https://github.com/Jonnytan555/FootyhubAWS.git
cd FootyhubAWS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **Important — Python 3.14 compatibility fix:**
> Ubuntu 26.04 ships with Python 3.14. Run this after install to pin working versions:
> ```bash
> pip install "fastapi==0.115.5" "starlette==0.41.3"
> ```

---

## 5. Create database tables

```bash
psql -h localhost -U footyhub -d footyhub -f sql/postgres_schema.sql
```

---

## 6. Configure environment variables

```bash
nano .env
```

```
ANTHROPIC_API_KEY=...
PERPLEXITY_API_KEY=...
JWT_SECRET=...

DB_HOST=localhost
DB_NAME=footyhub
DB_USER=footyhub
DB_PASSWORD=...

SQS_QUEUE_URL=https://sqs.eu-west-2.amazonaws.com/YOUR_ACCOUNT_ID/footyhub-articles
AWS_REGION=eu-west-2
```

---

## 7. Test the app runs

```bash
source venv/bin/activate
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

Visit `http://<ec2-public-ip>:8000` — you should see the feed.

---

## 8. Install systemd services

```bash
sudo cp deploy/footyhub-web.service /etc/systemd/system/
sudo cp deploy/footyhub-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable footyhub-web footyhub-scheduler
sudo systemctl start footyhub-web footyhub-scheduler
```

Check both are running:
```bash
sudo systemctl status footyhub-web
sudo systemctl status footyhub-scheduler
```

---

## 9. Configure nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/footyhub
sudo ln -s /etc/nginx/sites-available/footyhub /etc/nginx/sites-enabled/footyhub
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Visit `http://<ec2-public-ip>` (port 80) — nginx proxies to the app.

---

## 10. IAM role setup (SQS access)

1. In AWS Console → IAM → Roles → Create role → trusted entity: **EC2**
2. Create a policy from `deploy/iam-policy.json` (replace `YOUR_ACCOUNT_ID` with your real account ID)
3. Attach the policy to the role
4. Attach the role to the EC2 instance: **EC2 → Actions → Security → Modify IAM role**

This allows the publisher and subscriber to read/write SQS without hardcoded AWS credentials.

---

## Updating after code changes

```bash
cd ~/FootyhubAWS
git pull
source venv/bin/activate
sudo systemctl restart footyhub-web footyhub-scheduler
```

---

## Useful commands

| Command | Purpose |
|---------|---------|
| `sudo journalctl -u footyhub-web -f` | Stream web app logs |
| `sudo journalctl -u footyhub-scheduler -f` | Stream scheduler logs |
| `sudo systemctl restart footyhub-web` | Restart web app |
| `sudo systemctl restart footyhub-scheduler` | Restart scheduler |
| `sudo nginx -t` | Test nginx config before reload |
| `sudo -u postgres psql -d footyhub` | Connect to database directly |
