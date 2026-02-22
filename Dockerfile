# যে ইমেজের উপর ভিত্তি করে কন্টেইনার বানাবো
FROM python:3.11-slim

# কাজের ডিরেক্টরি সেট করা
WORKDIR /app

# প্রথমে requirements কপি করে ইনস্টল করি → ক্যাশিং এর জন্য ভালো
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# এখন পুরো প্রজেক্ট কপি করি
COPY . .

# পরিবেশ ভ্যারিয়েবল (অপশনাল)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# পোর্ট যেটা খুলবে
EXPOSE 8000

# সার্ভার চালানোর কমান্ড (ডেভেলপমেন্টের জন্য runserver)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]