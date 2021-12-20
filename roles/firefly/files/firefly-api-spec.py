#!/usr/bin/env python3
import requests
import yaml
import argparse
import logging

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--servername', help='')
parser.add_argument('--client', default='api', help='')
parser.add_argument('--secret', help='')
parser.add_argument('--contactname', default='Cequence', help='')
parser.add_argument('--contactemail', default='info@cequence.ai', help='')
parser.add_argument('--sentinel', help='')
parser.add_argument('--apiversion', default='1.5.4', help='')
parser.add_argument('--debug', action='store_true', default=False, help='')
args = parser.parse_args()

if args.debug:
    import requests.packages.urllib3.connectionpool as http_client
    http_client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

download_url = 'https://api-docs.firefly-iii.org/firefly-iii-' + args.apiversion + '.yaml'
r = requests.get(download_url)
r.raise_for_status()
spec = yaml.load(r.text, Loader=yaml.Loader)
spec['info']['contact']['name'] = args.contactname
spec['info']['contact']['email'] = args.contactemail

host_list = args.sentinel.split('.')
auth_host = 'auth' + '.' + '.'.join(host_list[1:])

login_data = {'client_id': args.client, 'client_secret': args.secret, 'grant_type': 'client_credentials'}
login_url = 'https://' + auth_host + '/auth/realms/cequence/protocol/openid-connect/token'
sentinel = requests.session()
sentinel.verify = False
r = sentinel.post(login_url, data=login_data)
r.raise_for_status()
token = r.json()['access_token']
sentinel.headers.update({'Authorization': 'bearer ' + token})

api_data = {'schemes': ['http', 'https'], 'servers': [args.servername], 'openApiSpec': yaml.dump(spec)}
r = sentinel.post('https://' + args.sentinel + '/apisec/api/dictionary/api-definitions', json=api_data)
r.raise_for_status()