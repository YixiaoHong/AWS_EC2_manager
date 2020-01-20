import threading

from flask import render_template, redirect, url_for, request, session, g
from app import webapp
import boto3
from app import config
from datetime import datetime, timedelta
from operator import itemgetter

from app.LogHelper import read_log, delete_log, write_log
from app.s3_monitor import clean_one_bucket
from app.loadbalacerhelper.LoadBalancerHelper import registerInstanceToLB, deregisterInstanceToLB, loadBalancerArn, \
    getInstanceAddr, getLBAddr
from app.sql.config.DbConfig import db_config
import mysql.connector
import time


# The function used to establish connection to sql database
def connect_to_database():
    return mysql.connector.connect(user=db_config['user'], password=db_config['password'], host=db_config['host'],
                                   database=db_config['database'], use_pure=True)


def get_database():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db


def instance_filter(instances):
    '''
    filtered list of instances pop manager instances, pop instances with status of "terminated"
    :param instances: The original query instances from boto3
    :return: filtered list of instances pop manager instances, pop instances with status of "terminated"
    '''
    newInstanceList = []
    for instance in instances:
        if not (instance.id == "i-0a4596b36ad81d462" or instance.state['Name'] == "terminated" or instance.state[
            'Name'] == "shutting-down"):
            # if is_instance_inelb(instance.id):
            newInstanceList.append(instance)
    return newInstanceList


@webapp.route('/ec2', methods=['GET'])
# Display an HTML list of all ec2 instances
def ec2_list():
    '''
    # Display an HTML list of all ec2 instances
    :return: rendered html page of ec2/list.html
    '''

    if 'authenticated' not in session or session['authenticated'] != True:
        return redirect(url_for('user_login'))

    # create connection to ec2
    ec2 = boto3.resource('ec2')
    #    instances = ec2.instances.filter(
    #        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    instances = ec2.instances.all()

    instances = instance_filter(instances)

    instancesPlotData = {}
    for instance in instances:
        cpuData, httpData = ec2_data_collect(instance.id)
        instancesPlotData[str(instance.id)] = [cpuData, httpData]

    instancesName = {}
    workerCount = 1
    for instance in instances:
        instance.dns = getInstanceAddr(instance.id)
        instance.isInlb = is_instance_inelb(instance.id)
        if instance.id == "i-0a4596b36ad81d462":
            instancesName[instance.id] = "Manager Server"
        else:
            instancesName[instance.id] = "Worker" + str(workerCount)
            workerCount = workerCount + 1

    info_msg = ""
    error_msg = ""

    if "info" in session:
        info_msg = session["info"]
        session.pop("info")

    if "error" in session:
        error_msg = session["error"]
        session.pop("error")
    log = read_log()
    logList = log.split("|||")

    lbdns = getLBAddr()
    return render_template("ec2/list.html", title="EC2 Instances", lbdns=lbdns, instances=instances,
                           instancesName=instancesName, instancesPlotData=instancesPlotData,
                           info_msg=info_msg, error_msg=error_msg, logList=logList)


def ec2_data_collect(id):
    '''
    This function collects AWS cloudwatch monitor data for a single instance search by its ID
    :param id: the string of desired instance ID
    :return: list of data for cpu plot, list of data for http plot
    '''
    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(id)
    client = boto3.client('cloudwatch')
    metric_name = 'CPUUtilization'
    ##    CPUUtilization, NetworkIn, NetworkOut, NetworkPacketsIn,
    #    NetworkPacketsOut, DiskWriteBytes, DiskReadBytes, DiskWriteOps,
    #    DiskReadOps, CPUCreditBalance, CPUCreditUsage, StatusCheckFailed,
    #    StatusCheckFailed_Instance, StatusCheckFailed_System
    namespace = 'AWS/EC2'
    statistic = 'Average'  # could be Sum,Maximum,Minimum,SampleCount,Average

    # CPU Monitor
    cpu = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName=metric_name,
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )
    cpu_stats = []
    for point in cpu['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        cpu_stats.append([time, point['Average']])
    cpu_stats = sorted(cpu_stats, key=itemgetter(0))

    # HTTP Monitor
    statistic = 'SampleCount'  # could be Sum,Maximum,Minimum,SampleCount,Average
    http_in = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName='request_received',
        Namespace='http_request_count',  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'requests', 'Value': id}]
    )
    http_in_stats = []
    for point in http_in['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        http_in_stats.append([time, point['SampleCount']])
    http_in_stats = sorted(http_in_stats, key=itemgetter(0))

    return cpu_stats, http_in_stats


@webapp.route('/ec2/create', methods=['POST'])
# Start a new EC2 instance
def ec2_create():
    '''
    This function create a new instance from the stored image, it will prevent creating more instances if there are already 10 working instances
    :return:redirect(url_for('ec2_list'))
    '''

    # ec2 = boto3.resource('ec2')
    # instances = ec2.instances.all()
    # workingWorkerCounter = 0
    # for instance in instances:
    #     if instance.id != "i-0a4596b36ad81d462" and \
    #             (instance.state['Name'] == "running" or instance.state['Name'] == "pending"):
    #         workingWorkerCounter += 1
    #
    # #if still have avaliable slots for new workers
    # if workingWorkerCounter < 10:
    #     newInstance = ec2.create_instances(ImageId=config.ami_id, MinCount=1, MaxCount=1, InstanceType='t2.small', KeyName="ECE1779_NEW")
    #     registerInstanceToLB(newInstance[0].id)
    #     session["info"] = "=== INFO: Created One Worker ! ==="
    # else:
    #     session["error"] = "=== ERROR: Unable to Create a Worker at this Moment ! ==="
    #
    # return redirect(url_for('ec2_list'))
    result = increase()
    if result:
        session["info"] = "=== INFO: Created One Worker ! ==="
    else:
        session["error"] = "=== ERROR: Unable to Create a Worker at this Moment ! ==="

    return redirect(url_for('ec2_list'))


@webapp.route('/ec2/delete/<id>', methods=['POST'])
# Terminate a EC2 instance
def ec2_destroy(id):
    '''
    Destroy a specific instance by ID
    :param id:
    :return:redirect(url_for('ec2_list'))
    '''
    # create connection to ec2
    ec2 = boto3.resource('ec2')
    deregisterInstanceToLB(id)
    ec2.instances.filter(InstanceIds=[id]).terminate()
    session["info"] = "=== INFO: Worker " + str(id) + " is Destroyed! ==="
    return redirect(url_for('ec2_list'))


@webapp.route('/ec2/delete_one', methods=['POST'])
# Terminate a EC2 instance
def ec2_destroy_one():
    '''
    destroy a working worker instance, if there are only one working instances, it wont delete any instances
    :return:redirect(url_for('ec2_list'))
    '''
    # create connection to ec2
    # ec2 = boto3.resource('ec2')
    # instances = ec2.instances.all()
    # task_finish_flag = 0
    # for instance in instances:
    #     if instance.id != "i-0a4596b36ad81d462" and instance.state['Name'] == "pending":
    #         ec2.instances.filter(InstanceIds=[instance.id]).terminate()
    #         task_finish_flag = 1
    #         session["info"] = "=== INFO: Destroyed One Worker ! ==="
    #         break
    #     if instance.id != "i-0a4596b36ad81d462" and instance.state['Name'] == "running":
    #         ec2.instances.filter(InstanceIds=[instance.id]).terminate()
    #         task_finish_flag = 1
    #         session["info"] = "=== INFO: Destroyed One Worker ! ==="
    #         break
    #
    # if task_finish_flag == 0:
    #     session["error"] = "=== ERROR: Unable to Destroy a Worker at this Moment ! ==="
    #
    # return redirect(url_for('ec2_list'))
    result = decrease()
    if result:
        session["info"] = "=== INFO: Destroyed One Worker ! ==="
    else:
        session["error"] = "=== ERROR: Unable to Destroy a Worker at this Moment ! ==="
    return redirect(url_for('ec2_list'))


@webapp.route('/ec2/stop_all', methods=['POST'])
# Stop all EC2 instance
def ec2_stop_all():
    '''
    This function terminates all the working worker instances and then stop the current manager server
    :return: redirect(url_for('ec2_list'))
    '''
    # create connection to ec2
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.all()
    for instance in instances:
        if instance.id != "i-0a4596b36ad81d462":
            ec2.instances.filter(InstanceIds=[instance.id]).terminate()

    ec2.instances.filter(InstanceIds=['i-0a4596b36ad81d462']).stop()

    session["info"] = "=== INFO: All Workers Destroyed, Manager Stopped! ==="

    return redirect(url_for('ec2_list'))


@webapp.route('/ec2/clear_data', methods=['POST'])
# clear database
def clear_database():
    '''
    This function clear all the stored files in S3 and than clear all the data tables in the database
    :return: redirect(url_for('ec2_list'))
    '''

    try:
        clean_one_bucket("ece1779assignment2")
        cnx = get_database()
        cursor = cnx.cursor()
        query = ''' TRUNCATE `ece1779`.`file_info`;'''
        cursor.execute(query)
        cnx.commit()
        time.sleep(1)
        query = ''' DELETE FROM `ece1779`.`user_info`'''
        cursor.execute(query)
        cnx.commit()
    except Exception as ex:
        write_log(ex)
        session["error"] = "=== ERROR: Can not Delete Data at This Moment ! ==="

    session["info"] = "=== INFO: All Application Data Deleted ! ==="
    return redirect(url_for('ec2_list'))


#
# def start_auto_scalling():
#     '''
#     No use anymore
#     :return:
#     '''
#     while True:
#         cnx = get_database()
#         cursor = cnx.cursor()
#         query = "SELECT * FROM autoscaler_config"
#         cursor.execute(query)
#         results = cursor.fetchall()
#         cpu_threshold_grow = 41
#         cpu_threshold_shrinking = 40
#         ratio_grow = 1.2
#         ratio_shrink = 1
#         time.sleep(5)

def increase():
    '''
    This function trys to increase a new instance, it will not create more instances is there are already 10 instances running and it register the created instance to the AWS autobalancer after the new instance is created.
    :return: True/False
    '''
    start_instance = threading.Thread(target=increaseHelper, args=[])
    start_instance.start()
    return True


def decrease():
    '''
    This function will try to terminate a running instance, it will not terminate the manager instance.
    :return: True/False
    '''
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.all()
    task_finish_flag = 0
    ins = []
    for instance in instances:
        ins.append(instance)
    ins.sort(key=sortByCreateTime, reverse=True)
    for instance in ins:
        if instance.id != "i-0a4596b36ad81d462" and instance.state['Name'] == "pending":
            ec2.instances.filter(InstanceIds=[instance.id]).terminate()
            return True
        elif instance.id != "i-0a4596b36ad81d462" and instance.state['Name'] == "running":
            ec2.instances.filter(InstanceIds=[instance.id]).terminate()
            return True

    return False


def sortByCreateTime(ins):
    return ins.launch_time


def is_instance_inelb(id):
    elbList = boto3.client('elbv2')
    ec2 = boto3.resource('ec2')
    result = ""

    bals = elbList.describe_target_health(
        TargetGroupArn=loadBalancerArn
    )
    for elb in bals['TargetHealthDescriptions']:
        insid = elb["Target"]['Id']
        if id == insid:
            return True
    return False


@webapp.route("/clean_log", methods=["GET"])
def clear_log():
    delete_log()
    return redirect(url_for('ec2_list'))


def increaseHelper():
    with webapp.app_context():
        ec2 = boto3.resource('ec2')
        instances = ec2.instances.all()
        workingWorkerCounter = 0
        cmd = '''
                    #!/bin/bash
                    kill -9 $(lsof -t -i:5000)
                    source /var/lib/jenkins/workspace/flaskvenv/bin/activate
                    gunicorn -b 0.0.0.0:5000 --chdir /var/lib/jenkins/workspace/ece1779-image-processing/ app:webapp
                    '''
        for instance in instances:
            if instance.id != "i-0a4596b36ad81d462" and \
                    (instance.state['Name'] == "running" or instance.state['Name'] == "pending"):
                workingWorkerCounter += 1

        # if still have avaliable slots for new workers
        if workingWorkerCounter < 10:
            newInstance = ec2.create_instances(ImageId=config.ami_id, MinCount=1, MaxCount=1, InstanceType='t2.small',
                                               KeyName="ECE1779_NEW", )
            newInstance[0].wait_until_running(
                Filters=[
                    {
                        'Name': 'instance-id',
                        'Values': [str(newInstance[0].id)]
                    }
                ]
            )
            registerInstanceToLB(newInstance[0].id)
            result = boto3.client('ec2').monitor_instances(InstanceIds=[str(newInstance[0].id)])
            return True
        else:
            return False
