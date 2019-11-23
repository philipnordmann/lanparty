import yaml
import argparse

def add(file, ips, interface):
    with open(file) as netplan_file:
        network_conf = yaml.load(netplan_file, Loader=yaml.SafeLoader)
    for ip in ips:
        if ip not in network_conf['network']['ethernets'][interface]['addresses']:
            network_conf['network']['ethernets'][interface]['addresses'].append(ip)
    with open(file, 'w') as netplan_file:
        yaml.dump(network_conf, netplan_file, Dumper=yaml.SafeDumper)

def remove(file, ips, interface):
    with open(file) as netplan_file:
        network_conf = yaml.load(netplan_file, Loader=yaml.SafeLoader)
    for ip in ips:
        if ip in network_conf['network']['ethernets'][interface]['addresses']:
            network_conf['network']['ethernets'][interface]['addresses'].remove(ip)
    with open(file, 'w') as netplan_file:
        yaml.dump(network_conf, netplan_file, Dumper=yaml.SafeDumper)


def main():
    parser = argparse.ArgumentParser(description="add / remove addresses to netplan")
    parser.add_argument("ips", metavar="N", type=str, nargs="+", help="ips to add")
    parser.add_argument("-f", "--netplanfile", help="path to netplan yaml file", required=True)
    parser.add_argument("-i", "--interface", help="interface to bind to", required=True)
    parser.add_argument("-a", "--action", help="add / remove ips", choices=['add', 'remove'], default='add')
    args = parser.parse_args()

    netplan = args.netplanfile
    ips = args.ips
    interface = args.interface
    action = args.action

    if action == "add":
        add(netplan, ips, interface)
    elif action == "remove":
        remove(netplan, ips, interface)


if __name__ == '__main__':
    main()
    