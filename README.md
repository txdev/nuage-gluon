# Nuage-Gluon Shim Layer
Nuage-Gluon Shim layer that is responsible for managing BGP-VPN ports.

The code has two parts:

* An etcd message listener that watches for upates from Gluon to create/delete ports.
* Split activation of VMs using Nuage APIs

## Etcd Listener
Etcd listener watches for port create/update/delete messages from Gluon. The listener has two threads. The main thread does a blocking call to watch for events. If an event occurs, the message is pushed to a queue. The second thread reads the queue and processes the message.

A message is processed only if the host is one of the manage compute hosts.

### Usage
> python setup.py install
> nuage-shim-server -H <etcd-hostname> -p <etcd-port> -v <vsd-ip> -d

## Nuage Split Activation of VMs using Python SDK
Activate VMs on Nuage. The VMs need to be instantiated on the compute using "virsh" command. 
Following VSD objects are created if they don't already exist.

	Domain
	Zone
	Subnet
	VPort
	rayh
	VM

### Setting up the environment

The commands have to be run under a virtualenv environment

    apt-get install python-virtualenv
    virtual-env vspk-env
    cd vspk-env
    source bin/activate
    
### Usage
#### NUSplitActivation class

    sa = NUSplitActivation(config)
    sa.activate()

#### Using command

    python vm_split_activation.py -c <config file> -v

### configuration

User has to provide following configuration parameters using config.ini file:

    [General]
    api_url=http://<ip>:8443
    username=<user-name>
    password=<password>
    enterprise=<enterprise-name>
    domain_template_name=<template-name>
    l2_domain_template_name=<l2-template-name>

    [Gluon] 
    enterprise_name= <enterprise-name>
    domain_name=<domain-name>
    domain_rt=<route-target>
    domain_rd=<route-distinguisher>
    zone_name=<zone-name>
    subnet_name=<subnet-name>
    vport_name=<vport-name>
    vm_name=<vm-name>
    vm_ip=<vm-ip-address>
    vm_uuid=<vm-uuid>
    netmask=<netmask>
    network_address=<network-address>
    vm_mac=<vm-mac-address>
    tunnel_type=<GRE|VXLAN>
