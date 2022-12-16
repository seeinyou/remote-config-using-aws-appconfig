import boto3
import json
import urllib.request
from botocore.exceptions import ClientError

'''
Parameters from requests
Path parameters:
- app: AWS AppConfig application identifier
- env: AWS AppConfig environment identifier
- config_profile_names: AWS AppConfig configuration profile name (should support multiple configuration profile names in the future)

QueryString parameters:
- flag: reserved parameter to retrieve specific one or more flags
- condition param names and values such as device_os = ios,etc.
'''

# JM's temproray method - should use Lambda extension later
appconfig_client = boto3.client('appconfigdata')

# Global configures
confident_score_threshold = 70 # Ignore the result when confident score is less than the threshold.
condition_priority_name = 'condition-priority'
default_error_msg = 'Get configuration from AppConfig failed!'


# Get configuration profiles from AWS AppConfig by calling APIs
def get_appconfig_config_by_layer(app, env, config_name, flags = []):
    try:
        url = f'http://localhost:2772/applications/{app}/environments/{env}/configurations/{config_name}'
        print('#LAYER_URL:', url) # Debug
    
        config = json.loads(urllib.request.urlopen(url).read())

        return config

    except ClientError as e:
        print('#ERROR get_appconfig_config_by_layer exception:', e)
        return False


# Get configuration profiles from AWS AppConfig by calling APIs
# def get_appconfig_config(app, env, config_name, mini_poll_sec = 15):
#     try:
#         # Get AppConfig session
#         session_response = appconfig_client.start_configuration_session(
#             ApplicationIdentifier = app,
#             EnvironmentIdentifier = env,
#             ConfigurationProfileIdentifier = config_name,
#             RequiredMinimumPollIntervalInSeconds = mini_poll_sec
#         )

#         if 'InitialConfigurationToken' in session_response:
#             config_response = appconfig_client.get_latest_configuration(
#                 ConfigurationToken = session_response['InitialConfigurationToken']
#             )

#             # appconfig_client.close()
#             print('# APPCONFIG RESULTS:', config_response)

#             # Get configurations from config_response['Configuration']
#             if 'Configuration' in config_response:
#                 return json.loads(config_response['Configuration'].read()) 

#     except ClientError as e:
#         print('#ERROR get_appconfig_config exception:', e)
#         return False


'''
  Lambda handler
  Get the condition priority list
  Get configurations
  Filter configurations using the condition priority list and return results
'''
def lambda_handler(event, context):
    check_cond = True # Check condition flag

    print("event: {}".format(event))
    path_params = event['pathParameters']
    request_params = event['queryStringParameters']
    print("PATH PARAMS: {}".format(path_params))
    print("QUERY PARAMS: {}".format(request_params))

    # Get condition priority
    raw_condition_priority = get_appconfig_config_by_layer(path_params['app'], path_params['env'], condition_priority_name)
    
    if raw_condition_priority:
        condition_priority_json = raw_condition_priority
    else:
        check_cond = False
        print('# WARNING: Get no conditions!')
        # return http_response(default_error_msg, 400)

    # Get configuration_profile
    raw_configs = get_appconfig_config_by_layer(path_params['app'], path_params['env'], path_params['config_profile_names'])

    if raw_configs:
        raw_configs_json = raw_configs
    else:
        return http_response(default_error_msg, 400)

    print('#CONDITION_PRIORITY:', condition_priority_json)
    print('#RAW_CONFIGS:', raw_configs_json)

    if check_cond:
        conditions = available_conditions(condition_priority_json, request_params)
        print('#AVAILABLE PRIORITY:', conditions)
    else:
        conditions = []

    if raw_configs_json:

        if check_cond:
            configs = {}

            for element in raw_configs_json:
                # print('### RAW ELEMENT:', element) # Debug

                tmp_configs = check_values(raw_configs_json[element], conditions)

                if tmp_configs:
                    configs[element] = tmp_configs
        else:
            configs = raw_configs_json  
        # print('#FILTERED CONFIGS:', configs) # Debug

    if configs:
        return http_response(json.dumps(configs))
    else:
        return http_response('Get remote configs failed', 400)


# Get active conditions comparing with request parameters
def available_conditions(condition_priority, request_params):
    conditions = []
    expression = ''

    for condition in condition_priority:

        if condition['param'] in request_params:
            expression = 'request_params["' + condition['param'] + '"]' + condition['expression']
            # print('#EXPRESSION:', expression) # Debug

            if eval(expression):
                conditions.append(condition)

    return conditions


# Check whether it uses conditional values or the default value
def check_values(element, condition_priority):
    '''
    Sample:
    element: {"canada":10,"default":3,"enabled":true}
    condition: {'name': 'ios', 'param': 'device_os', 'expression': " == 'ios'"
    '''
    results = {}

    if not condition_priority:
        return element
    # print('### ELEMENT:', element) # Debug

    if element['enabled'] == True:

        for condition in condition_priority:
            tmp_results = {}
            # print('### CONDITION:', condition) # Debug

            if condition['name'] in element and element[condition['name']]:
                tmp_results['values'] = element[condition['name']]
                # print('### TMP_RESULTS:', tmp_results) # Debug

                break # Break when the first condition is fulfilled

            if not tmp_results and 'default' in element: # Use default values when no condition fulfilled
                tmp_results['values'] = element['default']

        tmp_results['enabled'] = True

        results = tmp_results

    else:
        results = {"enabled": False}
    
    return results


# The function to generate HTTP response
def http_response(body = '', httpCode = 200):
    return {
        'statusCode': httpCode,
        'body': body
    }
