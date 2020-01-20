from flask import g
import boto3
from app.ec2_monitor import ec2_create, ec2_data_collect, instance_filter, ec2_destroy_one
from app.sql.config.DbConfig import db_config
import mysql.connector

# The function used to establish connection to sql database
def connect_to_database():
    return mysql.connector.connect(user=db_config['user'],password=db_config['password'],host=db_config['host'],database=db_config['database'],use_pure=True)

def get_database():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db


cnx = get_database()
cursor = cnx.cursor()
query = "SELECT * FROM autoscaler_config"
cursor.execute(query)
results = cursor.fetchall()
