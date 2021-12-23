# k8s-nfd-watcher

k8s-nfd-watcher is a custom Kubernetes controller that will restart pods if an external device is connected or disconnected (ie. webcams, 3D Printers). 

This controller requires that these 2 plugins are installed and configured in the cluster:
* [Node Feature Discovery](https://github.com/kubernetes-sigs/node-feature-discovery) - Customizable Kubernetes add-on that will dynamically add corresponding labels to nodes when a device is connected.
* [Smarter-Device-Manager](https://gitlab.com/arm-research/smarter/smarter-device-manager) - Registers devices with the Kubernetes device plugin framework to advertise system hardware resources to the kubelet.

## Current use cases:
* To automatically restart smarter-device-manager whenever a new device is connected to a node so that it is registered as an available node resource. Smarter-Device-Manager, on it's own, requires a manual restart to detect new devices.
* To delete pods whenever a node resource, that it has allocated, has been connected or disconnected.

## How it works:
When node-feature-discovery automatically adds or removes a label, nfd-watcher will delete all smarter-device-manager pods. This will trigger smarter-device-manager to rescan for new devices. nfd-watcher will detect any changes to new devices added as an allocatable resource on the node. Optionally, nfd-watcher can subsequently restart any pods that have requested a node resource managed by smarter-device-manager if that resource was changed (added, removed, updated).

## Installation instructions:
* Setup Node Feature Discover and Smarter Device Manager as per their instructions
* create a serviceaccount named nfd-watcher with cluster-admin role
* edit nfd-watcher-deployment.yaml with the desired namespace and apply (defaults to default namespace)

## config.yaml properties:
| Property | Default Value | Description |
| -------- | ------------- | ----------- |
| label_pattern | '^feature.node.kubernetes.io/' | The nfd-watcher pod will monitor nodes.metadata.labels for any changes in labels matching this pattern. |
| smarter_device_label | 'name=smarter-device-manager' | A change in node.metadata.labels matching the value of `label_pattern` will delete pods where pod.metadata.labels include a label matching the value of `smarter_device_label`. |
| allocatable_pattern | '^smarter-devices' | The nfd-watcher pod monitors all nodes for changes in node.status.allocatable where the child keys matches this pattern. |
| delete_pods_label | 'nfd-watcher-change-detected=delete' | Any pod with this label will be deleted if a change was detected in a requested node resource matching the value of `allocatable_pattern` |

The configuration file can be changed by using a configmap and replacing the file "/config/config.yaml" on the container.
