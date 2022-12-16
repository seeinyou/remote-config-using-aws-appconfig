import urllib.request
                

def lambda_handler(event, context):
    url = f'http://localhost:2772/applications/DemoApp/environments/prod/configurations/main'
    config = urllib.request.urlopen(url).read()
    return config