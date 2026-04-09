# Emergency SOS App - India

A production-ready Emergency SOS mobile application for India that handles the full lifecycle of an emergency event — from detection and dispatch through live tracking and family notification.

## 🚨 Features

- **Emergency Trigger & Triage**: SOS trigger with emergency type selector (cardiac, trauma, stroke, fire, accident)
- **Hospital Selection Engine**: PostGIS-powered nearby hospital ranking with weighted tier list (distance + rating + specialty match)
- **Real-time Bed Availability**: Integration point for ABDM/NHA APIs with mock implementation
- **Ambulance Dispatch & Live Tracking**: Real-time GPS updates via Redis pub/sub, Google Maps routing
- **Family Notification System**: SMS/push notifications to emergency contacts with live tracking links
- **Hospital-Ambulance Coordination**: Automated alerts to hospitals with ETA and bed reservation

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Mobile App    │────▶│   FastAPI Backend│────▶│  PostgreSQL     │
│  (React Native) │◀────│   (Async)        │◀────│  + PostGIS      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                        │
         │                       ▼                        │
         │              ┌──────────────────┐             │
         │              │      Redis       │─────────────┘
         │              │  (Cache/PubSub)  │
         │              └──────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│  Tracking Web   │     │  Twilio/FCM      │
│     Page        │     │  (SMS/Push)      │
└─────────────────┘     └──────────────────┘
```

## 📁 Project Structure

```
emergency-sos-app/
├── backend/
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Config, security
│   │   ├── db/             # Database connection
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── utils/          # Helpers
│   ├── migrations/         # Alembic migrations
│   └── requirements.txt
├── mobile/                 # React Native app
│   └── src/
├── tracking-web/           # Public tracking page
├── scripts/                # Seed scripts
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.9+
- Node.js 18+ (for mobile app)
- Google Maps API Key
- Twilio Account (for SMS)

### 1. Clone & Setup

```bash
cd emergency-sos-app
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` with your API keys:

```env
GOOGLE_MAPS_API_KEY=your_google_maps_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=+1234567890
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/emergency_sos
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
```

### 3. Start Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL + PostGIS
- Redis
- FastAPI Backend

### 4. Run Migrations & Seed Data

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Seed hospitals data
docker-compose exec backend python -m app.scripts.seed_hospitals
```

### 5. Access the API

- **API Docs**: http://localhost:8000/docs
- **Tracking Page**: http://localhost:8001/tracking/{token}

## 📱 Mobile App

### Install Dependencies

```bash
cd mobile
npm install
```

### Run on iOS/Android

```bash
# iOS
npx react-native run-ios

# Android
npx react-native run-android
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/emergency/trigger` | Start emergency, get hospital tier list |
| POST | `/emergency/{id}/confirm` | Confirm hospital, dispatch ambulance |
| GET | `/emergency/{id}/track` | Get live ambulance location + ETA |
| POST | `/emergency/{id}/update` | Push ambulance GPS update |
| GET | `/hospitals/nearby` | Get ranked hospitals by location |
| POST | `/contacts/notify` | Send SMS/push to emergency contacts |
| GET | `/tracking/{token}` | Public live tracking page |

## 🗄️ Database Models

- **users**: Profile, emergency contacts, medical info
- **hospitals**: Location (PostGIS), specialties, rating, beds
- **ambulances**: Current location, status, assignments
- **emergencies**: Emergency sessions with status tracking
- **emergency_updates**: Timeline of events per emergency

## 🌍 Hospital Coverage

Pre-seeded with 20+ hospitals across major Indian cities:
- Delhi NCR
- Mumbai
- Bangalore
- Chennai
- Kolkata
- Hyderabad
- Pune

Each hospital includes:
- Specialties (Cardiology, Trauma, Neurology, etc.)
- Star ratings (1-5)
- Bed capacity
- Real-time availability simulation

## 📊 Real-time Features

- **Redis Pub/Sub**: Live ambulance location streaming
- **WebSocket Support**: Real-time updates to mobile app
- **Google Maps Integration**: Live routing and ETA calculation
- **Twilio Integration**: SMS notifications at each milestone

## 🔐 Security

- JWT-based authentication
- Environment variable configuration
- CORS protection
- Input validation with Pydantic
- SQL injection prevention (async SQLAlchemy)

## 🧪 Testing

```bash
# Run tests
docker-compose exec backend pytest

# With coverage
docker-compose exec backend pytest --cov=app
```

## 📈 Monitoring

- Health check endpoint: `/health`
- Redis connection monitoring
- Database connection pooling
- Request logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

For emergencies, always call local emergency services first:
- **India Emergency Number**: 112
- **Ambulance**: 102
- **Police**: 100
- **Fire**: 101

---

Built with ❤️ for India's emergency response system
