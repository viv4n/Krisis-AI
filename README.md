# Krisis-AI
Krisis-AI 🚨

Real-time, AI-driven disaster response and triage mapping via SMS and Telegram.

When natural disasters strike, cellular data networks frequently collapse, leaving standard apps useless. Krisis-AI is a lightweight, low-bandwidth crisis management pipeline that allows victims to report emergencies using standard SMS or compressed Telegram messages. Our backend uses AI to instantly verify, deduplicate, and map these reports on a live tactical dashboard for first responders.

🌟 Key Features

Low-Bandwidth Input Pipelines: Accepts emergency reports via Telegram Bots and direct SMS (via Textbee integration).

AI Safety Net & Triage: Uses DistilBERT to analyze incoming text, filtering out noise/spam and assigning a priority score to genuine emergencies.

Intelligent Image Deduplication: Uses perceptual hashing (pHash) and Hamming distance calculations to detect and cluster duplicate photos from the same incident, preventing map clutter.

Smart Geocoding Fallbacks: Extracts addresses/landmarks from text using geopy. If no explicit location is provided, the system assigns a regional coordinate to ensure no SOS is lost.

Real-Time Tactical Map: A Next.js frontend powered by WebSockets instantly plots new emergencies on a live map and triage queue—no page refreshes required.

🛠️ Tech Stack

Frontend: Next.js, React, Tailwind CSS, Vercel (Deployment)

Backend: FastAPI, Python, SQLite (Database), WebSockets

Machine Learning: DistilBERT (Hugging Face) for NLP triage

Infrastructure: Ngrok (Secure Tunneling), Textbee (SMS Gateway), Telegram API

🚀 Local Setup & Installation

1. Clone the Repository

git clone https://github.com/YOUR_USERNAME/Krisis-AI.git
cd Krisis-AI


2. Backend Setup

Navigate to the backend directory and install the required Python packages.

cd backend
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt


Run the backend server:

python run.py


The FastAPI server will start on http://127.0.0.1:8000.

3. Frontend Setup

Open a new terminal, navigate to the frontend directory, and start the Next.js app.

cd frontend
npm install
npm run dev


The dashboard will be available at http://localhost:3000.

🔗 Environment Variables

Frontend (frontend/.env.local or Vercel Settings):

NEXT_PUBLIC_API_URL=https://your-ngrok-url.ngrok-free.dev
NEXT_PUBLIC_WS_URL=wss://your-ngrok-url.ngrok-free.dev


Backend (backend/.env):

TELEGRAM_BOT_TOKEN=your_telegram_token


(Make sure to point your Telegram Webhook to https://your-ngrok-url.../api/v1/telegram/webhook)

🧪 Testing the Pipeline (Simulating SMS)

Because physical Android SMS interception can be blocked by OEM battery savers, we have included a simulation script to test the backend logic and WebSocket broadcasting directly.

Ensure the backend and frontend are running.

Run the SMS simulation script:

python backend/simulate_sms.py


Watch the Next.js dashboard—a new incident will instantly appear on the map and in the triage queue!
