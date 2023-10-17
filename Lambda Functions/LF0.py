import json
import boto3

client = boto3.client('lexv2-runtime')


def lambda_handler(event, context):
    print(event)
    msg_from_user = event['messages'][0]['unstructured']['text']
    response = client.recognize_text(
        botId='FMC5KX0YWZ',
        botAliasId='YIEIRFIPV1',
        localeId='en_US',
        sessionId='testuser',
        text=msg_from_user
    )

    print(response)
    print(response['ResponseMetadata']['HTTPStatusCode'])

    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            "messages": [
                {
                    "type": "unstructured",
                    "unstructured": {
                        "id": "string",
                        "text": response['messages'][0]['content'],
                        "timestamp": "string"
                    }
                }
            ]
        }

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from LF0!')
    }