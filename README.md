# Privacy Eraser

Personal data removal SaaS - automatically remove your information from 100+ data broker sites.

## Features

- **Data Broker Removal** - Auto-submit opt-out requests to 100+ data broker sites
- **GDPR/CCPA Requests** - Generate deletion requests for major companies
- **Privacy Monitoring** - Continuous scanning for personal info exposure
- **Account Discovery** - Find forgotten accounts linked to email

## Deploy to Production

### One-Click Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/royyamamoto-rgb/privacy-eraser)

After deploying, configure these environment variables in your Render dashboard:

| Variable | Description |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Your Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `STRIPE_PRICE_BASIC` | Stripe price ID for Basic plan |
| `STRIPE_PRICE_PREMIUM` | Stripe price ID for Premium plan |
| `RESEND_API_KEY` | Resend.com API key for emails |

## Local Development

```bash
# Clone the repo
git clone https://github.com/royyamamoto-rgb/privacy-eraser.git
cd privacy-eraser

# Start all services
docker-compose up -d

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Tech Stack

- **Frontend**: Next.js 14, React, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI, Python 3.11, SQLAlchemy
- **Database**: PostgreSQL 15
- **Queue**: Redis + Celery
- **Scraping**: Playwright
- **Payments**: Stripe
- **Email**: Resend

## Pricing

| Plan | Price | Features |
|------|-------|----------|
| Free | $0/mo | 5 broker scans, manual removal |
| Basic | $5/mo | 50 broker scans, auto-removal, email support |
| Premium | $9/mo | Unlimited scans, priority removal, monitoring |

## License

MIT
