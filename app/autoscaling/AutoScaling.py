import datetime
import math
from datetime import timedelta
from time import sleep
from flask import g, render_template, request, redirect, url_for
import boto3

from app import webapp
from app.LogHelper import write_log, delete_log
from app.ec2_monitor import instance_filter, ec2_destroy_one, increase, decrease
from app.sql.config.DbConfig import db_config
import mysql.connector

time_interval = 60

isAutoScaling = True


@webapp.route("/triggerAutoScaling", methods=["POST"])
def triggerAutoScaling():
    '''
    This function will switch the on/off of the autoscaling service
    :return: redirect(url_for('show_param'))
    '''
    global isAutoScaling
    isAutoScaling = not isAutoScaling
    return redirect(url_for('show_param'))

# The function used to establish connection to sql database
def connect_to_database():
    return mysql.connector.connect(user=db_config['user'], password=db_config['password'], host=db_config['host'],
                                   database=db_config['database'], use_pure=True)


def get_database():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db


# @webapp.route('/update-auto-scale-param', methods=['POST'])
# def update_db():
#     print(request.form)
#     return render_template("auto_scaling.html", util = ave, cpugrow = cpuGrow, cpushrink = cpuShrink, ratiogrow = ratioGrow, ratioshrink = ratioShrink)

@webapp.route('/auto_scaling', methods=['GET', "POST"])
def show_param():
    '''
    Search the variable stored on the database and display the variables of the auto scalar
    :return: render_template "auto_scaling.html"
    '''
    cnx = get_database()
    cursor = cnx.cursor()
    if request.method == "POST":
        new_cpuGrow = request.form['cpugrow']
        new_cpuShrink = request.form['cpushrink']
        new_ratioGrow = request.form['ratiogrow']
        new_ratioShrink = request.form['ratioshrink']

        query = ''' UPDATE autoscaler_config SET threshold_grow = %s,threshold_shrink = %s,ratio_grow = %s,ratio_shrink = %s
                          WHERE acid = 1
        '''
        cursor.execute(query, (new_cpuGrow, new_cpuShrink, new_ratioGrow, new_ratioShrink))
        cnx.commit()

    query = "SELECT * FROM autoscaler_config"
    cursor.execute(query)
    results = cursor.fetchall()
    cpuGrow = results[0][1]
    cpuShrink = results[0][2]
    ratioGrow = results[0][3]
    ratioShrink = results[0][4]
    ave = auto_scaling(cpuGrow, cpuShrink, ratioGrow, ratioShrink)

    return render_template("auto_scaling.html", util=ave, cpugrow=cpuGrow, cpushrink=cpuShrink, ratiogrow=ratioGrow,
                           ratioshrink=ratioShrink, isAutoScaling=isAutoScaling)


def start_auto_scalling():
    '''
    Perform a continues loop and keeps checking if the average CPU meet the criteria of increasing/shrinking the instance
    :return:
    '''
    with webapp.app_context():
        write_log("Start Auto Scaling:")
        while True:
            if isAutoScaling:
                delete_log()
                write_log("=== === ===" + str(datetime.datetime.now()) + "=== === ===")
                cnx = get_database()
                cnx.connect()
                cursor = cnx.cursor()
                query = "SELECT * FROM autoscaler_config"
                cursor.execute(query)
                results = cursor.fetchall()
                cpu_threshold_grow = results[0][1]
                cpu_threshold_shrinking = results[0][2]
                ratio_grow = results[0][3]
                ratio_shrink = results[0][4]
                write_log("---> CPU Threshold grow: " + str(cpu_threshold_grow))
                write_log("---> CPU Threshold shrinking: " + str(cpu_threshold_shrinking))
                write_log("---> CPU ratio grow: " + str(ratio_grow))
                write_log("---> CPU ratio shrink: " + str(ratio_shrink))
                try:
                    auto_scaling(cpu_threshold_grow, cpu_threshold_shrinking, ratio_grow, ratio_shrink)
                except Exception as e:
                    write_log(e)
                write_log("=== === === === === === === === ===")
                sleep(time_interval)
                cnx.close()


def auto_scaling(cpu_threshold_grow, cpu_threshold_shrinking, ratio_grow, ratio_shrink):
    '''
    check if the average CPU of the instances in the past 2 minuets meet the criteria of increasing/shrinking the instance, if so, the function will excute the corresponding operation
    :param cpu_threshold_grow: cpu_threshold_grow rate
    :param cpu_threshold_shrinking: cpu_threshold_shrinking rate
    :param ratio_grow: ratio_grow rate
    :param ratio_shrink: ratio_shrink rate
    :return:
    '''
    with webapp.app_context():
        # getting average cpu utils

        ec2 = boto3.resource('ec2')
        #    instances = ec2.instances.filter(
        #        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        instances = ec2.instances.all()
        instances = instance_filter(instances)
        instancesCumCpuUtilData = 0
        write_log("---> Currently: " + str(len(instances)) + " instance(s) are registered under the load balancer and are running or pending")
        if len(instances) == 0:
            write_log("---> Currently no instance available, add one!")
            increase()
        instances = ec2.instances.all()
        instances = instance_filter(instances)
        for instance in instances:
            cpuData = cpuUtilHelper(instance.id)
            if len(cpuData['Datapoints']) != 0:
                write_log("---> Average for instance: " + str(cpuData['Datapoints'][0]['Average']))
                if instance.launch_time.replace(tzinfo=None) <= (datetime.datetime.utcnow() - timedelta(seconds=5 * 60)).replace(tzinfo=None):
                    instancesCumCpuUtilData += cpuData['Datapoints'][0]['Average']
                else:
                    cnx = get_database()
                    cnx.connect()
                    cursor = cnx.cursor()
                    query = "SELECT * FROM autoscaler_config"
                    cursor.execute(query)
                    results = cursor.fetchall()
                    adjustment = results[0][2]
                    write_log("---> The instance: " + str(instance.id) + " is just created. To avoid unusual high CPU util at the beginning of the boot, the current CPU util will be counted as "+str(adjustment)+" at this time. This instance's real CPU util will be counted and be used for auto-scaling after: " + str(instance.launch_time + timedelta(seconds=5 * 60)) + "!")
                    instancesCumCpuUtilData += adjustment
            else:
                write_log("---> Instance: " + str(instance.id) + "'s monitoring data is still under preparation.")
        average = instancesCumCpuUtilData / len(instances)
        write_log("---> Current average of all instances: " + str(average))
        # Enforcement
        # if average > 90 and len(instances) < 10:
        #     increase()
        # if average < 10 and len(instances) > 1:
        #     decrease()
        # User customizable cases:
        if average > cpu_threshold_grow:
            write_log("---> Start to increase instance: ")
            ctr = 0
            for i in range(len(instances), math.ceil(len(instances) * (ratio_grow))):
                ctr = ctr + 1
                write_log("------> Start to increase instance: " + str(ctr))
                increase()
                write_log("------> Completed the increment")
        elif average < cpu_threshold_shrinking:
            write_log("---> Start to decrease instance: ")
            ctr = 0
            lenth = len(instances)
            for i in range(len(instances), math.ceil(len(instances) * (ratio_shrink))):
                if lenth > 1:
                    ctr = ctr + 1
                    write_log("------> Start to decrease instance: " + str(ctr))
                    decrease()
                    lenth = lenth - 1
                    write_log("------> Completed the decrement")
                elif lenth == 0:
                    write_log("Oops, all the instances deleted :( ")
                    increase()
                    write_log("Reopened a new one :) ")
                else:
                    write_log("------> Oops, failed to delete the instance as there is only one instance left :( ")
        return average


def cpuUtilHelper(id):
    '''
    request boto3 cloudwatch service and get the average CPU usage of the specific instance during the past 2 minuets
    :param id:
    :return: average CPU rate
    '''
    with webapp.app_context():
        client = boto3.client('cloudwatch')
        metric_name = 'CPUUtilization'
        namespace = 'AWS/EC2'
        statistic = 'Average'  # could be Sum,Maximum,Minimum,SampleCount,Average
        cpu = client.get_metric_statistics(
            Period=1 * 60,
            StartTime=datetime.datetime.utcnow() - timedelta(seconds=2 * 60),
            EndTime=datetime.datetime.utcnow() - timedelta(seconds=0 * 60),
            MetricName=metric_name,
            Namespace=namespace,  # Unit='Percent',
            Statistics=[statistic],
            Dimensions=[{'Name': 'InstanceId', 'Value': id}]
        )
        return cpu