import json
import os
import logging
import boto3
import random
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from boto3.dynamodb.conditions import Key, Attr
from time import sleep

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

REGION = 'us-east-1'
HOST = 'search-restaurants-masked_information.us-east-1.es.amazonaws.com'
INDEX = 'restaurants'


def getSQSMsg():
    SQS = boto3.client("sqs")
    url = 'https://sqs.us-east-1.amazonaws.com/masked-information'
    response = SQS.receive_message(
        QueueUrl=url,
        AttributeNames=['SentTimestamp'],
        MessageAttributeNames=['All'],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )
    try:
        message = response['Messages'][0]
        if message is None:
            logger.debug("Empty message")
            return None
    except KeyError:
        logger.debug("No message in the queue")
        return None
    message = response['Messages'][0]
    SQS.delete_message(
        QueueUrl=url,
        ReceiptHandle=message['ReceiptHandle']
    )
    logger.debug('Received and deleted message: %s' % response)
    return message


def lambda_handler(event, context):
    message = getSQSMsg()
    if message is None:
        logger.debug("There was no message in the queue this time")
        return

    location = message["MessageAttributes"]["location"]["StringValue"]
    cuisine = message["MessageAttributes"]["cuisine"]["StringValue"]
    date = message["MessageAttributes"]["date"]["StringValue"]
    time = message["MessageAttributes"]["time"]["StringValue"]
    num_people = message["MessageAttributes"]["num_people"]["StringValue"]
    email = message["MessageAttributes"]["email"]["StringValue"]

    if not cuisine or not email:
        logger.debug("Cuisine or email not found in message")
        return

    q = {'size': 20, 'query': {'multi_match': {'query': cuisine}}}

    client = OpenSearch(hosts=[{
        'host': HOST,
        'port': 443
    }],
        http_auth=('master', 'masked_password'),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection)

    esq_data = client.search(index=INDEX, body=q)

    try:
        hits = esq_data['hits']['hits']
        es_query_response = []
        for hit in hits:
            es_query_response.append(hit['_source'])
    except KeyError:
        logger.debug("Error extracting data from Elastic Search")

    random.shuffle(es_query_response)

    rids = []
    for i in range(len(es_query_response)):
        rids.append(es_query_response[i]['Restaurant'])

    email_to_send = 'Hello! Here are {cuisine} restaurant suggestions in {location} for {num_people} people, for {diningDate} at {diningTime}:      '.format(
        cuisine=cuisine,
        location=location,
        num_people=num_people,
        diningDate=date,
        diningTime=time,
    )

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('yelp-restaurants')

    logger.debug("degugging error: rids {}".format(rids))

    it = 1
    for rid in rids:
        if it == 3:
            break
        resp = table.scan(FilterExpression=Attr('id').eq(rid))
        # sleep(0.1)
        logger.debug("degugging error for loop: {}".format(resp))
        if len(resp['Items']) != 0:
            item = resp['Items'][0]
            if resp is None:
                continue

            temp = str(it) + '. '
            name = item["name"]
            address = item["address"]
            coords = item["coordinates"]
            zipcode = item["zip_code"]
            rating = item["rating"]
            num_revs = item["num_reviews"]

            temp += name + ', located at ' + address + '. ' + 'Zipcode is ' + zipcode + '. '
            temp += 'Location Coordinates are: ' + coords + '. '
            temp += 'Rating: ' + rating + ' (num of reviews: {})   '.format(num_revs)

            email_to_send += temp
            it += 1
        else:
            pass

    email_to_send += "Have a great dining experience!!"
    logger.debug("EMAIL : {}".format(email_to_send))

    try:
        logger.debug("reached the try statement.")
        email_client = boto3.client('ses')
        email_resp = email_client.send_raw_email(
            Destinations=[email],
            FromArn='',
            RawMessage={
                'Data': email_to_send
            },
            ReturnPathArn='',
            Source='masked_email',
            SourceArn=''
        )
        logger.debug("response - %s", json.dumps(email_resp))
    except:
        logger.debug("Error sending the email.")

    logger.debug("Message = '%s' email = %s" % (email_to_send, email))

    return {
        'statusCode': 200,
        'body': json.dumps("LF2 running succesfully")
    }
