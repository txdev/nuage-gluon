# Create Gluon Port
Create Gluon port using Python VSDK. Following VSD objects are created if they don't already exist.

	Domain
	Zone
	Subnet
	VPort
	VM

## Usage
### GluonPort class

    gp = GluonPort(config)
    gp.create_port()

### create_gluon_port command

    python create_gluon_port.py -c <config file> -v

## configuration

User has to provide following configuration parameters using config.ini file:

    [General]
    username=
    password=
    enterprise=

    [Gluon]
    api_url= 
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
