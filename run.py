import os
from dotenv import load_dotenv
from app import create_app

# Load environment variables from .flaskenv
load_dotenv('.flaskenv')

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
