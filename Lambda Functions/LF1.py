import math
import dateutil.parser
import datetime
import time
import os
import logging
import boto3
import json
import re

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
SQS = boto3.client("sqs")

locations = ['manhattan']
cuisines = ['chinese', 'italian', 'french', 'japanese', 'mexican', 'indian', 'thai', 'korean', 'american']
email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'

def push2sqs(slots):
    """The lambda handler"""
    logger.debug("Recording with event %s", slots)
    try:
        u = 'https://sqs.us-east-1.amazonaws.com/329147244489/DCCBSQS'
        logging.debug("Got queue URL %s", u)
        resp = SQS.send_message(
            QueueUrl=u,
            MessageBody="Dining Concierge message from LF1",
            MessageAttributes={
                "location": {
                    "StringValue": str(slots['location']['value']['interpretedValue'].lower()),
                    "DataType": "String"
                },
                "cuisine": {
                    "StringValue": str(slots['cuisine']['value']['interpretedValue'].lower()),
                    "DataType": "String"
                },
                "date" : {
                    "StringValue": str(datetime.datetime.strptime(slots['date']['value']['interpretedValue'], '%Y-%m-%d').date()),
                    "DataType": "String"
                },
                "time" : {
                    "StringValue": str(datetime.datetime.strptime(slots['time']['value']['interpretedValue'], '%H:%M')).split(' ')[1],
                    "DataType": "String"
                },
                "num_people" : {
                    "StringValue": str(slots['num_people']['value']['interpretedValue']),
                    "DataType": "String"
                },
                "email" : {
                    "StringValue": str(slots['email']['value']['originalValue']),
                    "DataType": "String"
                }
            }
        )
        logger.debug("Send result: %s", resp)
    except Exception as e:
        raise Exception("Could not record link! %s" % e)

def check_email(email):
    # pass the regular expression
    # and the string into the fullmatch() method
    if (re.fullmatch(email_regex, email)):
        return True
    else:
        return False

def validate_order(slots):
    # Validate Location
    if not slots['location']:
        logger.debug('event.bot.log = Validating location')

        return {
            'isValid': False,
            'invalidSlot': 'location'
        }

    if slots['location']['value']['interpretedValue'].lower() not in locations:
        logger.debug('Invalid location')

        return {
            'isValid': False,
            'invalidSlot': 'location',
            'message': 'Please select a location among the following options: ({}).'.format(", ".join(locations))
        }


    # Validate Cuisine
    if not slots['cuisine']:
        logger.debug('event.bot.log = Validating cuisine')

        return {
            'isValid': False,
            'invalidSlot': 'cuisine'
        }

    if slots['cuisine']['value']['interpretedValue'].lower() not in cuisines:
        logger.debug('Invalid cuisine')

        return {
            'isValid': False,
            'invalidSlot': 'cuisine',
            'message': 'Please select a cuisine among the following options: ({}).'.format(", ".join(cuisines))
        }

    # Validate Date
    if not slots['date']:
        logger.debug('event.bot.log = Validating date')

        return {
            'isValid': False,
            'invalidSlot': 'date'
        }

    if (datetime.datetime.strptime(slots['date']['value']['interpretedValue'], '%Y-%m-%d').date() - datetime.datetime.today().date()).days < 0:
        logger.debug('Invalid date')

        return {
            'isValid': False,
            'invalidSlot': 'date',
            'message': 'Please select a date which is at least todays date: ({}).'.format(str(datetime.datetime.today().date()))
        }


    # Validate Time
    if not slots['time']:
        logger.debug('event.bot.log = Validating time')

        return {
            'isValid': False,
            'invalidSlot': 'time'
        }

    if ((datetime.datetime.strptime(slots['date']['value']['interpretedValue'], '%Y-%m-%d').date() == datetime.datetime.today().date()) and (datetime.datetime.strptime(slots['time']['value']['interpretedValue'], '%H:%M').hour < datetime.datetime.now().hour)):
        logger.debug('Invalid time')

        return {
            'isValid': False,
            'invalidSlot': 'time',
            'message': 'Please select a time which is greater than current time: ({}).'.format(str(datetime.datetime.now()) + ' EST')
        }

    # Validate Number of People
    if not slots['num_people']:
        logger.debug('event.bot.log = Validating num_people')

        return {
            'isValid': False,
            'invalidSlot': 'num_people'
        }

    if int(slots['num_people']['value']['interpretedValue']) < 1:
        logger.debug('Invalid num_people')

        return {
            'isValid': False,
            'invalidSlot': 'num_people',
            'message': 'Reservation can be done for at least 1 person. Please select a value that is at least 1'
        }

    # Validate email
    if not slots['email']:
        logger.debug('event.bot.log = Validating email')

        return {
            'isValid': False,
            'invalidSlot': 'email'
        }

    if not check_email(slots['email']['value']['originalValue']):
        logger.debug('Invalid email address')

        return {
            'isValid': False,
            'invalidSlot': 'email',
            'message': 'Please enter a valid email address'
        }

    # Valid Order
    return {'isValid': True}

def DiningSuggestions(event, intent, slots):
    order_validation_result = validate_order(slots)

    if event['invocationSource'] == 'DialogCodeHook':
        if not order_validation_result['isValid']:
            if 'message' in order_validation_result:
                response = {
                    "sessionState": {
                        "dialogAction": {
                            "slotToElicit": order_validation_result['invalidSlot'],
                            "type": "ElicitSlot"
                        },
                        "intent": {
                            "name": intent,
                            "slots": slots
                        }
                    },
                    "messages": [
                        {
                            "contentType": "PlainText",
                            "content": order_validation_result['message']
                        }
                    ]
                }
            else:
                response = {
                    "sessionState": {
                        "dialogAction": {
                            "slotToElicit": order_validation_result['invalidSlot'],
                            "type": "ElicitSlot"
                        },
                        "intent": {
                            "name": intent,
                            "slots": slots
                        }
                    }
                }
        else:
            response = {
                "sessionState": {
                    "dialogAction": {
                        "type": "Delegate"
                    },
                    "intent": {
                        'name': intent,
                        'slots': slots
                    }
                }
            }
    if event['invocationSource'] == 'FulfillmentCodeHook':
        response = {
            "sessionState": {
                "dialogAction": {
                    "type": "Close"
                },
                "intent": {
                    "name": intent,
                    "slots": slots,
                    "state": "Fulfilled"
                }

            },
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": "You’re all set. Expect my suggestions shortly! Have a good day."
                }
            ]
        }

        push2sqs(slots)

    return response

def thank_you(intent, slots):
    response = {
        "sessionState": {
            "dialogAction": {
                "type": "Close"
            },
            "intent": {
                "name": intent,
                "slots": slots,
                "state": "Fulfilled"
            }

        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": "You are welcome. Have a great day!!"
            }
        ]
    }
    return response

def greeting(intent, slots):
    response = {
        "sessionState": {
            "dialogAction": {
                "type": "Close"
            },
            "intent": {
                "name": intent,
                "slots": slots,
                "state": "Fulfilled"
            }

        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": "Hi there, how can I help?"
            }
        ]
    }
    return response

def lambda_handler(event, context):
    print(event)

    bot = event['bot']['name']
    slots = event['sessionState']['intent']['slots']
    intent = event['sessionState']['intent']['name']

    os.environ['TZ'] = 'America/New_York'
    time.tzset()

    logger.debug('event.bot.Session_ID = {}'.format(event['sessionId']))
    logger.debug('event.bot.name = {}'.format(bot))
    logger.debug('event.bot.slots = %s'%(slots))
    logger.debug('event.bot.intent = %s' %(intent))

    if intent == 'GreetingIntent':
        return greeting(intent, slots)
    elif intent == 'ThankYouIntent':
        return thank_you(intent, slots)
    elif intent == 'DiningSuggestionsIntent':
        return DiningSuggestions(event, intent, slots)

    raise Exception('Intent with name ' + intent + ' not supported')