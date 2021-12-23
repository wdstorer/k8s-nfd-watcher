import requests
import os
import json
import yaml
import logging
import sys
import time
import re

log = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
out_hdlr.setLevel(logging.INFO)
log.addHandler(out_hdlr)
log.setLevel(logging.INFO)

CONFIG_FILE = './config/config.yaml'

base_url = "http://127.0.0.1:8001"

namespace = os.getenv("res_namespace", "default")

def read_config(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return yaml.safe_load(f)
    else:
        log.info("{} not found. Exiting.".format(CONFIG_FILE))
        sys.exit(1)

def delete_pods(label, names=[]):
    url = "{}/api/v1/namespaces/{}/pods?labelSelector={}".format(base_url, namespace, label)
    r = requests.get(url)
    response = r.json()

    if len(names) == 0:
        pods = [p['metadata']['name'] for p in response['items']]
    else:
        pods = [p['metadata']['name'] for p in response['items'] if p['metadata']['name'] in names]

    for p in pods:
        url = "{}/api/v1/namespaces/{}/pods/{}".format(base_url, namespace, p)
        r = requests.delete(url)
        if r.status_code == 200:
            log.info("{} was deleted successfully".format(p))
        else:
            log.error("Could not delete {}".format(p))

def restart_smarterdevice_dependant_pods(previousState, currentState, object_name, delete_pods_label):
    deviceChanges = {d[0] for d in set(previousState.items()) ^ set(currentState.items())}
    url = "{}/api/v1/namespaces/{}/pods".format(base_url, namespace)
    r = requests.get(url)
    response = r.json()
    resource_requests = {sublist['metadata']['name']:x['resources'] for sublist in response['items'] for x in sublist['spec']['containers'] if delete_pods_label.split('=')[0] in sublist['metadata']['labels']}
    for pod in resource_requests.items():
        if 'requests' in pod[1]:
            for device in deviceChanges:
                if device in pod[1]['requests']:
                    log.info('{} has been modified on node {}. Deleting pod {}'.format(device, object_name, pod[0]))
                    delete_pods(delete_pods_label,[pod[0]])
                    
def event_loop(app_config):
    log.info("Starting nfd-watcher controller")
    url = '{}/api/v1/nodes?watch=true"'.format(base_url)
    r = requests.get(url, stream=True)
    labelState = {}
    lastSmarterDeviceState = {}
    smarterDeviceStateHashes = {}
    for line in r.iter_lines():
        obj = json.loads(line)
        event_type = obj['type']
        object_name = obj["object"]["metadata"]["name"]
        object_smarter_devices = {k:v for k,v in obj["object"]["status"]["allocatable"].items() if re.match(app_config['allocatable_pattern'], k)}
        smarter_devices_hash = hash(tuple(object_smarter_devices.items()))
        object_labels = {k:v for k,v in obj["object"]["metadata"]["labels"].items() if re.match(app_config['label_pattern'], k)}
        labels_hash = hash(tuple(object_labels.items()))

        if event_type == "ADDED":
            if object_name not in labelState:
                log.info('Loading current labelState for node {}'.format(object_name))
                labelState[object_name] = labels_hash

            if object_name not in smarterDeviceStateHashes:
                log.info('Loading current smarter-device state for node {}'.format(object_name))
                smarterDeviceStateHashes[object_name] = smarter_devices_hash
                lastSmarterDeviceState[object_name] = object_smarter_devices

        if event_type == "MODIFIED":
            if object_name in labelState:
                if labelState[object_name] != labels_hash:
                    log.info('NFD labels updated on node {}. Deleting smarter-device pods.'.format(object_name))
                    delete_pods(app_config['smarter_device_label'])
                    labelState[object_name] = labels_hash
            else:
                labelState[object_name] = labels_hash

            if object_name in smarterDeviceStateHashes:
                if smarterDeviceStateHashes[object_name] != smarter_devices_hash:
                    restart_smarterdevice_dependant_pods(lastSmarterDeviceState[object_name], object_smarter_devices, object_name, app_config['delete_pods_label'])
                    smarterDeviceStateHashes[object_name] = smarter_devices_hash
                    lastSmarterDeviceState[object_name] = object_smarter_devices
            else:
                smarterDeviceStateHashes[object_name] = smarter_devices_hash

if __name__ == '__main__':
    sleepTime = 5

    watcher_config = read_config(CONFIG_FILE)

    while True:
        try:  
            event_loop(watcher_config)
        except Exception as e:
            log.info('ERROR - Will try to reestablish stream again in {} seconds: {}'.format(str(sleepTime), e))
            time.sleep(sleepTime)

