---
description: Simple microblog web app with posts, voting, and dark mode
details: >
  A Flask-based microblogging application where users can create posts, upvote or downvote content,
  sort posts by recency or popularity, and toggle between light and dark mode. Includes user authentication
  and localStorage-based preference management for dark mode.
technologies:
  - flask
  - sqlite
  - jwt
hostedUrl: 
---
 

# Microblog

A simple microblogging web application where users can create posts, upvote/downvote posts, and interact with other users. The app includes authentication, voting functionality, sorting, and a dark mode.

## Features

### User Authentication
- Users can **register**, **login**, and **logout**.
- Authentication is handled using **Flask-Login**.

### Posts
- Users can **create posts** with a title and content.
- Posts are displayed in order (either by most recent or most upvoted).

### Voting System
- Users can **upvote** or **downvote** posts.
- Net votes are displayed (upvotes minus downvotes).
- Users can see their votes with visual feedback (highlighted buttons for voted posts).
- Users who are not logged in see a tooltip prompting them to log in to vote.

### Sorting
- Users can sort posts by **Most Recent** or **Most Upvoted** using a dropdown menu.

### Dark Mode
- Users can switch between **light mode** and **dark mode**, with preferences stored in `localStorage`.

## Setup Instructions

### 1. Clone the Repository
```sh
git clone https://github.com/Micmada/microblog.git
cd microblog
```

### 2. Create and Activate a Virtual Environment(Optional)
```sh
python -m venv venv
source venv/bin/activate  # On Mac/Linux
venv\Scripts\activate    # On Windows
```

### 3. Install Dependencies
```sh
pip install -r requirements.txt
```

### 4. Set Up the Environment Variables
Create a `.env` file in the root of the project and add the following:
```
SECRET_KEY=your_secret_key_here
SQLALCHEMY_DATABASE_URI=sqlite:///microblog.db  # Or your preferred database
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```
> **Note:** For Gmail, you need to create an **App Password** instead of using your normal password. You can generate it in your Google Account settings under "Security" > "App Passwords".

### 5. Run the Application
```sh
python app.py
```
Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Deployment
For deploying to a cloud platform like **Heroku**, **Render**, or **Railway**, ensure:
- The `.env` variables are set in the platform's environment configuration.
- A production-ready database (e.g., PostgreSQL) is used instead of SQLite.

## Contributing
Feel free to fork the repo and submit pull requests!


