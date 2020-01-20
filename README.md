# aws_EC2_manager
A dynamic resource management web-app which manages the working aws EC2 instances

##Environment:
- Python 3.5 (or better)
- A python virtual environment
- Flask
- Boto3 (AWS Python SDK)
- AWS CLI 

##Instruction


- Create a new python virtual environment as follows:
```
   python -m venv venv
```
- Install Flask
```
   venv/bin/pip install flask
````
- Install AWS Command Line Interface (CLI)

   Follow instruction in https://aws.amazon.com/cli/

- Install Boto3
```
   venv/bin/pip install boto3
```

- Configure aws credentials
```
   aws configure
```
- Run the app
```
   run.py
```
