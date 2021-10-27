from sys import argv, stderr
from os import path
from requests import get, post
import json
import re
from datetime import datetime, timedelta


SCRIPT = path.basename(argv[0])
VERSION = '0.1'
SECRETS_FILE = 'secrets.json'
WEATHER_FILE = 'weather.json'
LOG_FILE = 'nest_log.json'

# TODO: use /etc or %appdata% to store json files


class RequestError(Exception):
    error = 'RequestError'
    code = ''
    message = 'Unknown error'
    status = ''

    def __init__(self, data={}):
        if 'error' in data:
            if isinstance(data['error'], dict):
                self.error = 'error'
                if 'code' in data['error']:
                    self.code = data['error']['code']
                if 'message' in data['error']:
                    self.message = data['error']['message']
                if 'status' in data['error']:
                    self.status = data['error']['status']
                super().__init__(self.message)
                return
            self.error = data['error']
            if 'error_description' in data:
                self.message = data['error_description']
        if 'cod' in data:
            self.code = data['cod']
        if 'message' in data:
            self.message = data['message']
        super().__init__(self.message)


def first_run(filename=SECRETS_FILE):
    s = {}
    print(f'\n*** {SCRIPT} v{VERSION} Setup ***\n')

    print('\n*** READ ALL DIRECTIONS CAREFULLY! ***\n')

    print('First, create an OpenWeatherMap account and get an API key:')
    print('  https://home.openweathermap.org/users/sign_up\n')
    s['owm_key'] = input('Enter OWM API key > ')
    s['lat'] = float(input('Enter your latitude (dd.ddd format) > '))
    s['lon'] = float(input('Enter your longitude (dd.ddd format) > '))

    print('\nNext, follow Google\'s directions to register for device access.')
    print('  https://developers.google.com/nest/device-access/get-started\n')
    input('Press enter to continue once registered...')

    print('\nOpen your Cloud Platform Credentials page and create a project.')
    print('  https://console.cloud.google.com/apis/credentials\n')
    print('  Next, click CREATE CREDENTIALS and select OAuth Client ID, then Web Application')
    print('  Add https://www.google.com to the Authorized Redirect URI section\n')
    s['client_id'] = input('Enter client_id > ')
    s['client_secret'] = input('Enter client_secret > ')

    print('\nBe sure to visit the OAuth consent screen and add yourself as a test user.')
    print('  https://console.cloud.google.com/apis/credentials/consent\n')
    input('Press enter to continue...')

    print('\nOpen the Device Access Console and create a project')
    print('  https://console.nest.google.com/device-access/project-list')
    print('  Enter your OAuth client information during project creation.\n')
    s['project_id'] = input('Enter project_id > ')

    print('\nVisit the following link to authorize access to your devices:')
    print(f'  https://nestservices.google.com/partnerconnections/{s["project_id"]}/auth?redirect_uri=https://www.google.com&access_type=offline&prompt=consent&client_id={s["client_id"]}&response_type=code&scope=https://www.googleapis.com/auth/sdm.service')
    print('\n  You will be redirected to another URL at the end of this step.')
    print('  It will look like this: https://www.google.com?code=authorization-code&scope=https://www.googleapis.com/auth/sdm.service')
    print('  Copy the code parameter (between code= and the next &) and paste it below:\n')

    s['authorization_code'] = input('Enter authorization_code > ')

    print('\nGetting access and refresh tokens...')
    url = 'https://www.googleapis.com/oauth2/v4/token'
    access_data = {
        'client_id': s['client_id'],
        'client_secret': s['client_secret'],
        'code': s['authorization_code'],
        'grant_type': 'authorization_code',
        'redirect_uri': 'https://www.google.com'
    }
    r = post(url, access_data)
    tokens = json.loads(r.text)
    s['refresh_token'] = tokens['refresh_token']
    s['access_token'] = tokens['access_token']

    print(f'\nrefresh_token={s["refresh_token"]}')
    print(f'access_token={s["access_token"]}')

    print('\nGetting device info...', end='')
    s['devices'] = []
    id_pattern = re.compile('[^/]+$')
    devices = get_devices(s)['devices']
    print(f'found {len(devices)} devices:')
    for device in devices:
        d = {}
        d['id'] = id_pattern.search(device['name']).group()
        d['displayName'] = device['parentRelations'][0]['displayName']
        d['day_temp'] = 72.0
        d['night_temp'] = 69.0
        d['hysteresis'] = 3.0
        d['day_offset'] = -60.0
        d['night_offset'] = 240.0
        d['max_uv_offset'] = 18.0
        d['mid_uv_offset'] = 14.0
        d['min_uv_offset'] = 12.0
        d['morning_offset'] = 60.0
        d['evening_offset'] = 120.0
        s['devices'].append(d)
        print(f'  {d["displayName"]}')
    with open(filename, 'w') as f:
        f.write(json.dumps(s, indent=4))
    print(f'\nSetup complete.  Saved {filename} - customize it as desired.\n')
    return s


def load_json_file(filename):
    with open(filename) as f:
        data = json.load(f)
    return data


def get_devices(secrets):
    url = f'https://smartdevicemanagement.googleapis.com/v1/enterprises/{secrets["project_id"]}/devices'
    r = get(url, headers={'Authorization': f'Bearer {secrets["access_token"]}',
                          'Content-Type': 'application/json'})
    response = json.loads(r.text)
    if 'error' in response:
        raise RequestError(response)
    return response


def get_device(secrets, dev_num=0):
    url = f'https://smartdevicemanagement.googleapis.com/v1/enterprises/{secrets["project_id"]}/devices/{secrets["devices"][dev_num]["id"]}'

    r = get(url, headers={'Authorization': f'Bearer {secrets["access_token"]}',
                          'Content-Type': 'application/json'})
    response = json.loads(r.text)
    if 'error' in response:
        raise RequestError(response)
    return response


def refresh_access_token(secrets, filename=SECRETS_FILE):
    url = f'https://www.googleapis.com/oauth2/v4/token'
    refresh_data = {
        'client_id': secrets['client_id'],
        'client_secret': secrets['client_secret'],
        'refresh_token': secrets['refresh_token'],
        'grant_type': 'refresh_token'
    }
    r = post(url, refresh_data)
    response = json.loads(r.text)
    if 'access_token' in response:
        secrets['access_token'] = response['access_token']
        with open(filename, 'w') as f:
            f.write(json.dumps(secrets, indent=4))
        return secrets
    raise RequestError(response)


def get_wrapper(func, secrets, *args, **kwargs):
    # try the request - if it fails, refresh the access_token and try again
    try:
        return func(secrets, *args, **kwargs)
    except RequestError as e:
        refresh_access_token(secrets)
        return func(secrets, *args, **kwargs)  # let error propagate this time


def fahrenheit(c):
    return (c * 1.8) + 32.0


def celsius(f):
    return (f - 32.0) / 1.8


def get_weather(secrets, filename=WEATHER_FILE):
    url = 'https://api.openweathermap.org/data/2.5/onecall'
    query = {
        'lat': secrets['lat'],
        'lon': secrets['lon'],
        'units': 'imperial',
        'exclude': 'minutely,hourly,daily,alerts',
        'appid': secrets['owm_key']
    }
    r = get(url, params=query)
    response = json.loads(r.text)
    if 'current' in response:
        with open(filename, 'w') as f:
            f.write(json.dumps(response, indent=4))
        return response
    raise RequestError(response)


def adjust_set_point_to_feel(t, rh):  # fahrenheit
    # Steadman formula for temps < ~80°F
    # https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml
    feels_like = 0.5 * (t + 61.0 + ((t-68.0)*1.2) + (rh*0.094))
    return 2.0 * t - feels_like  # set point adjusted for relative humidity


def get_set_temp(secrets, weather, device_index=0):
    time_now = datetime.now()
    day = datetime.fromtimestamp(weather['current']['sunrise']) + \
        timedelta(minutes=secrets['devices'][device_index]['day_offset'])
    night = datetime.fromtimestamp(weather['current']['sunset']) + \
        timedelta(minutes=secrets['devices'][device_index]['night_offset'])
    if day < time_now < night:
        return secrets['devices'][device_index]['day_temp']
    return secrets['devices'][device_index]['night_temp']


def get_threshold(secrets, weather, set_point, device_index=0):
    time_now = datetime.now()
    morning = datetime.fromtimestamp(weather['current']['sunrise']) + \
        timedelta(minutes=secrets['devices'][device_index]['morning_offset'])
    evening = datetime.fromtimestamp(weather['current']['sunset']) + \
        timedelta(minutes=secrets['devices'][device_index]['evening_offset'])
    uv_percent = weather['current']['uvi'] / 10.0
    min_offset = secrets['devices'][device_index]['min_uv_offset']
    max_offset = secrets['devices'][device_index]['mid_uv_offset']
    if morning <= time_now <= evening:
        min_offset = secrets['devices'][device_index]['mid_uv_offset']
        max_offset = secrets['devices'][device_index]['max_uv_offset']
    offset = uv_percent * (max_offset - min_offset) + min_offset
    return set_point - offset


def set_temp_range(secrets, device_index, temps):
    url = f'https://smartdevicemanagement.googleapis.com/v1/enterprises/{secrets["project_id"]}/devices/{secrets["devices"][device_index]["id"]}:executeCommand'
    command = json.dumps({
        'command': 'sdm.devices.commands.ThermostatTemperatureSetpoint.SetRange',
        'params': {
            'heatCelsius': temps[0],
            'coolCelsius': temps[1]
        }
    })
    r = post(url, command, headers={'Authorization': f'Bearer {secrets["access_token"]}',
                                    'Content-Type': 'application/json'})
    response = json.loads(r.text)
    if 'error' in response:
        raise RequestError(response)
    return response


if __name__ == ('__main__'):
    log = {}

    log['datetime'] = {'date': datetime.strftime(datetime.now(), '%Y%m%d'),
                       'time': datetime.strftime(datetime.now(), '%H%M')}
    log['errors'] = {}

    secrets = load_json_file(SECRETS_FILE) if path.exists(
        SECRETS_FILE) else first_run()

    try:
        weather = get_weather(secrets, WEATHER_FILE)
    except RequestError as e:
        print(f'Error: {e.code} {e.error} - {e.message}', file=stderr)
        log['errors']['weather'] = f'{e.code} {e.error} - {e.message}'
        weather = load_json_file(WEATHER_FILE)  # use old weather

    log['weather'] = {'tempF': weather['current']['temp'],
                      'uvi': weather['current']['uvi']}

    for device_index in range(len(secrets['devices'])):
        device_name = secrets['devices'][device_index]['displayName']
        log[device_name] = {}
        log['errors'][device_name] = {}

        try:
            device = get_wrapper(get_device, secrets, device_index)
        except RequestError as e:
            print(f'Error: {e.code} {e.error} - {e.message}', file=stderr)
            log['errors'][device_name]['device'] = f'{e.code} {e.error} - {e.message}'
            continue

        humidity = device['traits']['sdm.devices.traits.Humidity']['ambientHumidityPercent']
        set_temp = get_set_temp(secrets, weather, device_index)
        log[device_name]['set_point_raw'] = set_temp
        set_temp = adjust_set_point_to_feel(set_temp, humidity)
        hysteresis = secrets['devices'][device_index]['hysteresis']
        threshold = get_threshold(secrets, weather, set_temp, device_index)
        outdoor_temp = float(weather['current']['temp'])
        temp_range = round(celsius(set_temp - hysteresis),
                           4), round(celsius(set_temp), 4)
        if outdoor_temp < threshold:
            temp_range = round(celsius(set_temp), 4), round(
                celsius(set_temp + hysteresis), 4)

        device_mode = device['traits']['sdm.devices.traits.ThermostatMode']['mode']
        if device_mode != 'HEATCOOL':
            log['errors'][device_name][f'mode_{device_mode}'] = f'Automation disabled - set HEATCOOL to enable'
            continue
        device_eco = device['traits']['sdm.devices.traits.ThermostatEco']['mode']
        if device_eco != 'OFF':
            log['errors'][device_name][f'eco_{device_eco}'] = f'Automation disabled - set Eco mode OFF to enable'
            continue

        try:
            set_temp_range(secrets, device_index, temp_range)
        except RequestError as e:
            print(f'Error: {e.code} {e.error} - {e.message}', file=stderr)
            log['errors'][device_name]['set_temp'] = f'{e.code} {e.error} - {e.message}'
            continue

        log[device_name]['relative_humidity'] = humidity
        log[device_name]['set_point_adj'] = round(set_temp, 2)
        log[device_name]['set_point_range'] = round(fahrenheit(
            temp_range[0]), 2), round(fahrenheit(temp_range[1]), 2)
        log[device_name]['threshold_temp'] = round(threshold, 2)
        log[device_name]['threshold_offset'] = round(set_temp - threshold, 2)
        if log['errors'][device_name] == {}:
            log['errors'].pop(device_name)

    if log['errors'] == {}:
        log.pop('errors')

    with open(LOG_FILE, 'w') as f:
        f.write(json.dumps(log, indent=4))
