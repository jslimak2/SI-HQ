# Post9 Deployment Guide

## Production Deployment

### Prerequisites
- Python 3.12+
- Redis (for caching)
- Firebase project (for authentication and data storage)
- SSL certificate for HTTPS

### Environment Setup

1. **Clone the repository:**
```bash
git clone https://github.com/jslimak2/Post9.git
cd Post9
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install production dependencies:**
```bash
pip install -r requirements-production.txt
```

4. **Configure environment variables:**
Create a `.env` file with:
```env
# Firebase Configuration
FIREBASE_API_KEY=your_api_key
FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_STORAGE_BUCKET=your_project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your_sender_id
FIREBASE_APP_ID=your_app_id

# Sports API
SPORTS_API_KEY=your_sports_api_key

# Service Account
GOOGLE_APPLICATION_CREDENTIALS=./path/to/service-account.json
```

### Production Server

#### Using Gunicorn (Recommended)

1. **Install Gunicorn:**
```bash
pip install gunicorn
```

2. **Start production server:**
```bash
gunicorn --bind 0.0.0.0:8000 --workers 4 production:application
```

#### Using Docker

1. **Create Dockerfile:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements-production.txt .
RUN pip install -r requirements-production.txt

COPY . .
EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "production:application"]
```

2. **Build and run:**
```bash
docker build -t sihq .
docker run -p 8000:8000 sihq
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/Post9/dashboard/static/;
        expires 1y;
        add_header Cache-Control public;
    }
}
```

### Security Checklist

- [ ] Use HTTPS with valid SSL certificate
- [ ] Set up proper firewall rules
- [ ] Configure rate limiting
- [ ] Use strong Firebase security rules
- [ ] Regular security updates
- [ ] Monitor application logs
- [ ] Backup strategy in place

### Monitoring

1. **Application logs:** Check `/logs/sihq.log`
2. **System monitoring:** Use tools like Prometheus/Grafana
3. **Uptime monitoring:** Set up external monitoring service
4. **Error tracking:** Consider using Sentry or similar

### Maintenance

- Regular dependency updates
- Log rotation setup
- Database backup automation
- Performance monitoring
- Security audit schedule

## Development Setup

For development, use:
```bash
cd dashboard
python app.py
```

This runs in debug mode with hot reloading.

## Troubleshooting

### Common Issues

1. **Firebase connection errors:**
   - Verify service account key path
   - Check Firebase project settings

2. **Sports API failures:**
   - Verify API key validity
   - Check rate limits

3. **Performance issues:**
   - Enable Redis caching
   - Check ML model loading times
   - Monitor memory usage

### Support

For deployment support, check:
- Application logs in `/logs/`
- System resource usage
- Network connectivity
- Environment variable configuration

---

**Last Updated**: 9/13/2025