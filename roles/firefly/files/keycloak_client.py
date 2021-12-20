#!/usr/bin/env python3
from kubernetes import client, config
import base64
import requests
import argparse
import sys
requests.packages.urllib3.disable_warnings()

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--clientname', default='Defender', help='Client name')
parser.add_argument('--namespace', default='sentinel', help='API Sentinel namespace')
parser.add_argument('--secretname', default='keycloak-admin-user', help='Keycloak admin user secret')
parser.add_argument('--ingressname', default='auth', help='API Sentinel Auth Ingress')
parser.add_argument('--realmname', default='cequence', help='Keycloak realm')
parser.add_argument('--create', action='store_true', default=False, help='Create this client')
parser.add_argument('--admin', action='store_true', default=False, help='Create this client as an admin')
args = parser.parse_args()

config.load_kube_config()
corev1 = client.CoreV1Api()
netv1 = client.NetworkingV1Api()

username = None
password = None
for s in corev1.list_namespaced_secret(namespace=args.namespace).to_dict()['items']:
    if s['metadata']['name'] == args.secretname:
        username = base64.b64decode(s['data']['username'])
        password = base64.b64decode(s['data']['password'])
if not username and not password:
    print("Secret '%s' not found" % args.secretname)
    sys.exit(1)

host = None
for s in netv1.list_namespaced_ingress(namespace=args.namespace).to_dict()['items']:
    if s['metadata']['name'] == args.ingressname:
        host = 'https://' + s['spec']['rules'][0]['host']
if not host:
    print("Ingress '%s' not found" % args.ingressname)
    sys.exit(1)

login_data = {'client_id': 'admin-cli', 'grant_type': 'password', 'username': username, 'password': password}
base_url = host + '/auth/admin/realms'
keycloak = requests.session()
keycloak.verify = False
r = keycloak.post(host + '/auth/realms/master/protocol/openid-connect/token', data=login_data)
r.raise_for_status()
token = r.json()['access_token']
keycloak.headers.update({'Authorization': 'bearer ' + token})

secret = None
if args.create:
    create_data = {'clientId': args.clientname,
                   'directAccessGrantsEnabled': True,
                   'serviceAccountsEnabled': True,
                   'authorizationServicesEnabled': True,
                   'attributes': {'access.token.lifespan': 300}}
    r = keycloak.post(base_url + '/' + args.realmname + '/clients', json=create_data)
    r.raise_for_status()

r = keycloak.get(base_url + '/' + args.realmname + '/clients', params={'clientId': args.clientname})
r.raise_for_status()
if len(r.json()) != 1:
    print("Keycloak client '%s' not found" % args.clientname)
    sys.exit(1)
id = r.json()[0]['id']

if args.admin:
    r = keycloak.get(base_url + '/' + args.realmname + '/roles')
    r.raise_for_status()
    composite_roles = []
    for role in r.json():
        if role['composite']:
            composite_roles.append(role)
    sa_id = keycloak.get(base_url + '/' + args.realmname + '/clients/' + id + '/service-account-user').json()['id']
    r = keycloak.post(base_url + '/' + args.realmname + '/users/' + sa_id + '/role-mappings/realm', json=composite_roles)
    r.raise_for_status()

r = keycloak.get(base_url + '/' + args.realmname + '/clients/' + id + '/client-secret')
r.raise_for_status()
secret = r.json()['value']

print(secret)
