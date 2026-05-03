import os
from dotenv import load_dotenv
from flask import Flask
from flask_mysqldb import MySQL

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

app.config['MYSQL_HOST']        = os.getenv('MYSQL_HOST')
app.config['MYSQL_PORT']        = int(os.getenv('MYSQL_PORT'))
app.config['MYSQL_USER']        = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD']    = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB']          = os.getenv('MYSQL_DB')
app.config['MYSQL_CURSORCLASS'] = 'Cursor'

mysql = MySQL(app)