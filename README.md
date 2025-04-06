# 🤖 Django AI Agent Bot App

An interactive AI-powered chatbot built with Django (backend) and Next.js (frontend), integrated with OpenAI's language models to intelligently process and respond to user requests.

---

## 🚀 Getting Started

Follow the steps below to get the application up and running locally.

---

### 🔁 1. Clone the Repository

```bash
git clone https://github.com/Project-Rocket-IO/Judy-s-Repository.git
cd Judy-s-Repository
```

---

### 🔐 2. Add Your OpenAI API Key

In the file:

```
/backend/chatbot_app/views.py
```

Look for the placeholder where the OpenAI token is needed and insert your key:

```python
openai.api_key = "your-openai-token-here"
```

---

### 🐍 3. Set Up Python Environment

Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Then install the backend dependencies:

```bash
pip install -r requirements.txt
```

---

### 📦 4. Install Node.js & Frontend Dependencies

Make sure Node.js and npm are installed:

```bash
npm -v
node -v
```

If not, install them from [https://nodejs.org/](https://nodejs.org/).

Then install the frontend framework (Next.js):

```bash
npm install next
```

And navigate to the frontend directory to install app dependencies:

```bash
cd frontend
npm install
```

---

### ⚙️ 5. Run the App

#### ✅ Start the Django Backend

From the `/backend` directory:

```bash
cd ../backend
python manage.py runserver
```

#### 🧠 Start the Frontend

From the `/frontend` directory:

```bash
cd ../frontend
npm run dev
```

---

## 🎉 You're Live!

Your Django + Next.js AI Agent Bot should now be running locally!  
The frontend will typically be available at:  
[http://localhost:3000](http://localhost:3000)  
And the backend at:  
[http://localhost:8000](http://localhost:8000)

---

## 💠 Tech Stack

- **Backend**: Django, Django REST Framework
- **AI Engine**: OpenAI API (GPT)
- **Frontend**: Next.js (React)
- **Environment**: Python, Node.js

---

## 📬 Questions or Suggestions?

Feel free to open an issue or submit a pull request in the [GitHub repo](https://github.com/Project-Rocket-IO/Judy-s-Repository.git)!

---

