from flask import render_template, redirect, url_for, request, session
from app import webapp
import boto3



@webapp.route('/s3',methods=['GET'])
def s3_list():
    '''
    This function Display an HTML list of all s3 buckets.
    :return: render_template "s3/list.html"
    '''
    if 'authenticated' not in session or session['authenticated'] != True:
        return redirect(url_for('user_login'))

    # Let's use Amazon S3
    s3 = boto3.resource('s3')
    # Print out bucket names
    buckets = s3.buckets.all()
    for b in buckets:
        name = b.name
    buckets = s3.buckets.all()

    bucket_size_dict = {}
    for bucket in buckets:
        bucket_size_dict[bucket.name] = len(list(bucket.objects.all()))

    info_msg = ""
    error_msg = ""

    if "info" in session:
        info_msg = session["info"]
        session.pop("info")

    if "error" in session:
        error_msg = session["error"]
        session.pop("error")

    return render_template("s3/list.html", title="s3 Instances", buckets=buckets,
                           info_msg=info_msg, error_msg=error_msg, bucket_size_dict = bucket_size_dict)


@webapp.route('/s3/<id>',methods=['GET'])
def s3_view(id):
    '''
    This function displays the details about a specific bucket.
    :param id:
    :return: render_template "s3/view.html"
    '''
    if 'authenticated' not in session or session['authenticated'] != True:
        return redirect(url_for('user_login'))

    s3 = boto3.resource('s3')
    bucket = s3.Bucket(id)
    for key in bucket.objects.all():
        k = key
    keys = bucket.objects.all()

    if len(list(keys)) == 0:
        session["info"] = "=== INFO: There is no file in this bucket! ==="

    info_msg = ""
    error_msg = ""

    if "info" in session:
        info_msg = session["info"]
        session.pop("info")

    if "error" in session:
        error_msg = session["error"]
        session.pop("error")

    return render_template("s3/view.html", title="S3 Bucket Contents", id=id, keys=keys, info_msg=info_msg, error_msg=error_msg)

@webapp.route('/s3/clean_bucket/<id>',methods=['GET'])
def clean_one_bucket(id):
    '''
    This function implement the boto3 to clean all the files in the s3 bucket
    :param id:
    :return: redirect(url_for('s3_list'))
    '''
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(id)
    bucket.objects.all().delete()
    session["info"] = "=== INFO: Bucket \"" + str(id) + "\" Cleared ! ==="
    return redirect(url_for('s3_list'))


@webapp.route('/s3/upload/<id>',methods=['POST'])
def s3_upload(id):
    '''
    This function uploads a file onto the s3 server
    :param id:
    :return: return redirect(url_for('s3_view', id=id))
    '''
    # check if the post request has the file part
    if 'new_file' not in request.files:
        return redirect(url_for('s3_view',id=id))

    new_file = request.files['new_file']

    # if user does not select file, browser also
    # submit a empty part without filename
    if new_file.filename == '':
        return redirect(url_for('s3_view', id=id))

    s3 = boto3.client('s3')

    s3.upload_fileobj(new_file, id, new_file.filename)

    return redirect(url_for('s3_view', id=id))

