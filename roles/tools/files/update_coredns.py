#!/usr/bin/env python3
from kubernetes import client, config
import argparse
import sys

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--ip', required=True, help='host IP address')
parser.add_argument('--fqdn', required=True, help='host fqdn')
parser.add_argument('--configname', default='coredns', help='name of coredns configmap')
parser.add_argument('--namespace', default='kube-system', help='namespace of configmap')
args = parser.parse_args()

config.load_kube_config()
corev1 = client.CoreV1Api()

cm = None
for c in corev1.list_namespaced_config_map(namespace='kube-system').to_dict()['items']:
    if c['metadata']['name'] == args.configname:
        cm = c

if not cm:
    print("ConfigMap '%s' not found in namespace '%s'" % (args.configname, args.namespace))
    sys.exit(1)

corefile = cm['data']['Corefile']
entry = '       ' + args.ip + ' ' + args.fqdn + '\n'
start = corefile.find('hosts {\n')
if start > -1:
    start += len('hosts {\n')
else:
    entry = '    hosts {\n' + entry + '       fallthrough\n    }\n'
    start = corefile.find('prometheus :9153\n') + len('prometheus :9153\n')

updated_corefile = corefile[:start] + entry + corefile[start:]
cm['data']['Corefile'] = updated_corefile

response = corev1.patch_namespaced_config_map(args.configname, args.namespace, cm)
sys.exit(0)
