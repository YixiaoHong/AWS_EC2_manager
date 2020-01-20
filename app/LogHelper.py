def write_log(log):
    '''
    This function writes the log string to the log file
    :param log:
    :return:
    '''
    file = open("logging.txt", "a")
    print(str(log))
    file.write(str(log) + "|||")
    file.close()

def read_log():
    '''
    This function read all the contents in the log file and return as string
    :return:
    '''
    file = open("logging.txt", "r")
    return file.read()

def delete_log():
    '''
    This function clear the content in the log file
    :return:
    '''
    file = open("logging.txt", "w")
    file.write("")
    file.close()