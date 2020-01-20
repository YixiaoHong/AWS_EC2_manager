import boto3

loadBalancerArn = "arn:aws:elasticloadbalancing:us-east-1:116102215986:targetgroup/ece1779/8d0366ade0f61943"

def registerInstanceToLB(id):
    '''
    This function register a specific instance to the loadbalancer
    :param id:
    :return:
    '''
    client = boto3.client('elbv2')
    response = client.register_targets(
        TargetGroupArn=loadBalancerArn,
        Targets=[
            {
                'Id': id
            },
        ]
    )

def deregisterInstanceToLB(id):
    '''
    This function removes a instance from the loadbalancer controlled instances list
    :param id:
    :return:
    '''
    client = boto3.client('elbv2')
    response = client.deregister_targets(
        TargetGroupArn=loadBalancerArn,
        Targets=[
            {
                'Id': id
            },
        ]
    )

def getLBAddr():
    elbList = boto3.client('elbv2')
    ec2 = boto3.client('ec2')

    bals = elbList.describe_load_balancers()

    return 'http://' + str(bals['LoadBalancers'][0]['DNSName'])

def getInstanceAddr(id):
    elbList = boto3.client('elbv2')
    ec2 = boto3.client('ec2')
    instance = ec2.describe_instances(InstanceIds=[id])
    result = "Initializing"
    try:
        result='http://' + instance['Reservations'][0]['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicDnsName']
    finally:
        return str(result)