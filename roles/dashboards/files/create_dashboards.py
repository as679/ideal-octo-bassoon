#!/usr/bin/env python3
import os
import argparse
import copy
import json
from kubernetes import client, config

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--namespace', default='monitoring', help='')
parser.add_argument('--sentinelpath', default='./api-sentinel/files/grafana-dashboards/', help='')
parser.add_argument('--defenderpath', default='./defender/grafana-dashboard/', help='')
args = parser.parse_args()

config.load_kube_config()
corev1 = client.CoreV1Api()

metadata_template = { 'name':      '',
                      'namespace': args.namespace,
                      'labels':      { 'grafana_dashboard': '1' },
                      'annotations': { 'k8s-sidecar-target-directory': '/tmp/dashboards/cequence' }}

for path in [ args.sentinelpath, args.defenderpath]:
    for filename in os.listdir(path):
        if os.path.isfile(path + filename) and filename.endswith('.json'):
            with open(path + filename) as fh:
                data = json.load(fh)
            md = copy.deepcopy(metadata_template)
            md['name'] = 'cequence-dashboard-' + filename.replace('_', '-')
            configmap = client.V1ConfigMap(kind='ConfigMap', metadata=md, data={filename: json.dumps(data)})
            corev1.create_namespaced_config_map(namespace=args.namespace, body=configmap)
