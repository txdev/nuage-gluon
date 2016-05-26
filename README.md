# Nuage Split Activation of VMs using Python SDK
Activate VMs on Nuage. The VMs need to be instantiated on the compute 
using "virsh" command. 
Following VSD objects are created if they don't already exist.

	Domain
	Zone
	Subnet
	VPort
	VM

## Usage
### NUSplitActivation class

    sa = NUSplitActivation(config)
    sa.activate()

### Using command

    python vm_split_activation.py -c <config file> -v

## configuration

User has to provide following configuration parameters using config.ini file:

    [General]
    api_url=
    username=
    password=
    enterprise=

    [Gluon] 
    enterprise_name= VSDK_Test
    domain_name=TestDomain
    domain_rt=20001
    domain_rd=20002
    zone_name=Zone0
    subnet_name=Subnet0
    vport_name=VPort2
    vm_name=testvm2
    vm_ip=10.23.120.10
    vm_uuid=53912732-8d33-4d82-8be0-1321b41b43ed
    netmask=255.255.255.0
    network_address=10.23.120.11
    vm_mac=fa:16:3e:66:2a:4a
