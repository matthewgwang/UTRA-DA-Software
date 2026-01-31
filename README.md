# UTRA Data Analysis Software

Flask + React project for robot telemetry analysis.

## Structure

- `backend/` - Flask API server
- `frontend/` - React dashboard
- `bridge/` - Python serial bridge script
- `arduino/` - EEPROM logger code

## Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
