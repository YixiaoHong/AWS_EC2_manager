import urllib

import boto3
from flask_bcrypt import Bcrypt
from flask import render_template, redirect, url_for, request, session, g, render_template_string
from app import webapp
import datetime

from app.loadbalacerhelper.LoadBalancerHelper import loadBalancerArn
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



@webapp.route('/',methods=['GET'])
@webapp.route('/index',methods=['GET'])
@webapp.route('/main',methods=['GET'])
# Display an HTML page with links
def main():
    '''
    This function checks the user credential in the session and if the user has the credential it it will redirect to the secured page, if not it eill redirect to the login page
    :return: redirect(url_for('user_login')) or redirect(url_for('user_login'))
    '''
    if ('authenticated' in session) and ('username' in session):
        #check if the cookie includes username and authenticated flag
        if session['authenticated'] == True:
            return render_template("main.html", title="MainPage",username=session['username'])
        else:
            if 'username' in session:
                session.pop('username')
            if 'authenticated' in session:
                session.pop('authenticated')
            return redirect(url_for('user_login'))
    else:
        if 'username' in session:
            session.pop('username')
        if 'authenticated' in session:
            session.pop('authenticated')
        return redirect(url_for('user_login'))

@webapp.route('/login',methods=['GET'])
def user_login():
    '''
    This function lead the user to the login page of the website
    :return: render_template("/manager_login.html", title="Welcome")
    '''
    return render_template("/manager_login.html", title="Welcome")

@webapp.route('/login_submit', methods=['POST'])
def login_submit():
    '''
    This function takes POST http request with URL of "/login_submit". It firstly reads the user submitted username,
    password and the check statue of "remember me" option based on whether the user checked "remember me" the function
    adjust the session expiry time by adjusting the value of webapp.permanent_session_lifetime. The function then
    connects to the database and reads the search results based on user inputs. If no search results find based on
    the user provided username, the function will return the user with "login_index.html" with error message; if the
    user input password doesn't match the database password after bcrypt,the function will return the user with
    login_index.html" with error message; If it passed all the condition, the function will redirect to URL"/secure/index"
    :return: /login_index.html or /secure/index

    '''
    session.permanent = True
    bcrypt = Bcrypt(webapp)
    username = request.form['username']
    password = request.form['password']
    #if remember!=None and remember=="on":
    #password = bcrypt.generate_password_hash(password).decode("utf-8")
    #bcrypt.check_password_hash
    # connect to database
    cnx = get_database()
    cursor = cnx.cursor()
    query = "SELECT password FROM manager_info WHERE username = %s and active = 1"
    cursor.execute(query, (username,))
    results = cursor.fetchall()
    if len(results)==1:
        hashed_pwd = results[0][0]
        if bcrypt.check_password_hash(hashed_pwd,password):
            session['authenticated'] = True
            session['username'] = username
            session['error'] = None
            return redirect(url_for('sensitive'))

    session['username'] = username
    session['error'] = "<=Error! Incorrect username or password!=>"

    return render_template("/manager_login.html", title="Main Page", username = username, error=session['error'])

"""
#############################################################
Secure Index
############################################################
"""
@webapp.route('/secure/index', methods=['GET', 'POST'])
def sensitive():
    '''
    This function takes GET/POST http request with URL of "/secure/index". The function firstly check if the user
    session has key of “authenticated” and value of True which indicating the user has passed the security check.
    If not, the user will be redirected back  to ‘/user_login’. If the user session contains “authenticated” and
    has a value of True, the function will perform a database search based on the “username” in the client’s
    session and store the user’s uid, upload_counter and create_date into the session and return the page
    of "/secured_index.html".
    :return: "/secure/index" or  "/secured_index.html"
    '''

    if 'authenticated' not in session:
        return redirect(url_for('user_login'))

    #==========Read user Info and sign in =========#
    if session['authenticated'] == True:
        return render_template("/main.html", title = "Welcome to Manager Control Panel :)")
    else:
        return redirect(url_for('user_login'))

@webapp.route('/logout', methods=['GET', 'POST'])
def logout():
    '''
    This function takes GET/POST http request with URL of “/logout”. The function clear all the contents in the
    current user’s session and terminate the user’s session’s lifetime. The function then redirect the user to
    the main page.
    :return: /secure/index
    '''
    session.clear()
    #webapp.permanent_session_lifetime = datetime.timedelta(milliseconds=0)
    return redirect(url_for("sensitive"))

# @webapp.route('/info', methods=['GET'])
# def info():
#     '''
#     Display DNS link for all the current running instances
#     :return: render_template_string(result)
#     '''
#     elbList = boto3.client('elbv2')
#     ec2 = boto3.client('ec2')
#
#     bals = elbList.describe_load_balancers()
#
#     result = '{% extends "base.html" %}{% block content %}<div><p>ELB DNS Name : </p></div><div><a href=\'http://' + str(
#         bals['LoadBalancers'][0]['DNSName']) + '\'> ' + str(bals['LoadBalancers'][0]['DNSName']) + '</a>'
#
#     bals = elbList.describe_target_health(TargetGroupArn=loadBalancerArn)
#     for elb in bals['TargetHealthDescriptions']:
#         insid = elb["Target"]['Id']
#         instance = ec2.describe_instances(InstanceIds = [insid])
#         dns = instance['Reservations'][0]['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicDnsName']
#         result = result + "<p>--->   Instance DNS: <a href=\'http://"+ dns + "\'>" + dns +"</a></p>"
#     result = result + "</div>{% endblock %}"
#     return render_template_string(result)

