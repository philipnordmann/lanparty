#!/usr/bin/env python3

import yaml
import argparse
import configparser
import os
import netifaces
import platform    # For getting the operating system name
import subprocess  # For executing a shell command
import sys


def ping(host):
    """
    Returns True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP) request even if the host name is valid.
    """

    # Option for the number of packets as a function of
    param = '-n' if platform.system().lower()=='windows' else '-c'

    # Building the command. Ex: "ping -c 1 google.com"
    command = ['ping', param, '1', host]

    return subprocess.call(command) == 0


def create_compose(services):
    with open('etc/base-compose.yml') as compose_file:
        compose = yaml.load(compose_file, Loader=yaml.SafeLoader)

    activated_services = dict()

    for service in services:
        with open('etc/services/{0}/{0}.yml'.format(service)) as service_file:
            compose['services'].update(yaml.load(service_file, Loader=yaml.SafeLoader))
    with open('docker-compose.yml', 'w+') as compose_file:
        yaml.dump(compose, compose_file, Dumper=yaml.SafeDumper)


def create_env_file(var_ips, services):    
    env_list = list()
    kv = '{}={}'

    env_list.append(kv.format('SERVICES_IP', var_ips['services_ip']['ip']))

    for service in services:
        ip_var = services[service]['ip_var']
        ip = var_ips[ip_var]['ip']
        insert = kv.format(ip_var.upper(), ip)
        if not insert in env_list:
            env_list.append(insert)

    for service in services:
        for arg in services[service]:
            if arg != 'ip_var':
                insert = kv.format(arg.upper(), services[service][arg])
                env_list.append(insert)
    
    for setting in GENERAL_CONFIG:
        if setting not in ['start_host', 'end_host']:
            insert = kv.format(setting.upper(), GENERAL_CONFIG[setting])
            env_list.append(insert)

    with open('.env', 'w') as env_file:
        env_file.write('\n'.join(env_list))


def get_free_ips(var_list, interface):
    ip_dict = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]
    own_ip = ip_dict['addr']
    netmask_cidr = ip_dict['netmask']
    netmask_bits = sum([bin(int(x)).count('1') for x in netmask_cidr.split('.')])
    ip_parts = own_ip.split('.')[:3]
    ip_str = '.'.join(ip_parts) + '.{host}'
    free_ips = list()

    for host in range(START_HOST, END_HOST):
        ip = ip_str.format(host=host)
        if not ping(ip):
            free_ips.append(ip)
            if len(free_ips) >= len(var_list):
                break

    return_dict = dict()
    with open('var/.freeips', 'w') as freeip_file:
        for i in range(0, len(free_ips)):
            return_dict[var_list[i]] = {'ip': free_ips[i], 'ip_netmask': free_ips[i] + '/' + str(netmask_bits)}
            print(return_dict[var_list[i]]['ip_netmask'], file=freeip_file)

    return return_dict


def add_ips(file, ips, interface):
    with open(file) as netplan_file:
        network_conf = yaml.load(netplan_file, Loader=yaml.SafeLoader)
    for ip in ips:
        if ip not in network_conf['network']['ethernets'][interface]['addresses']:
            network_conf['network']['ethernets'][interface]['addresses'].append(ip)
    with open(file, 'w') as netplan_file:
        yaml.dump(network_conf, netplan_file, Dumper=yaml.SafeDumper)


def remove_ips(file, ips, interface):
    with open(file) as netplan_file:
        network_conf = yaml.load(netplan_file, Loader=yaml.SafeLoader)
    for ip in ips:
        if ip in network_conf['network']['ethernets'][interface]['addresses']:
            network_conf['network']['ethernets'][interface]['addresses'].remove(ip)
    with open(file, 'w') as netplan_file:
        yaml.dump(network_conf, netplan_file, Dumper=yaml.SafeDumper)


def start(services, interface, netplanfile):
    ip_var_list = list()
    for service in services:
        ip_var = services[service]['ip_var']
        if ip_var not in ip_var_list:
            ip_var_list.append(ip_var)
    var_ips = get_free_ips(ip_var_list, interface)
    i = 0
    freeips = [var_ips[s]['ip_netmask'] for s in var_ips.keys()]
    add_ips(netplanfile, freeips, interface)
    subprocess.call(['netplan', 'apply'])

    create_compose(services)
    create_env_file(var_ips, services)


def stop():
    print('stop...')


def parse_args(services):
    parser = argparse.ArgumentParser(description="start lanparty services")
    parser.add_argument("action", type=str, help="start / stop the party", choices=['start', 'stop'])
    parser.add_argument("-f", "--netplanfile", help="path to netplan yaml file you want to change", required=True)
    parser.add_argument("-i", "--interface", help="interface to bind to", required=True)
    parser.add_argument("-s", "--services", help="additional services you want to start.\nfound: {}".format(" ".join(services)),
                        nargs='+', default='*')
    return parser.parse_args()


def main():
    if not os.path.isdir('var'):
        os.mkdir('var')
    found_services = os.listdir('etc/services/')
    args = parse_args(found_services)
    config_file = 'etc/settings.ini'
    config = configparser.ConfigParser()
    config.read(config_file)
    global START_HOST
    START_HOST = int(config['general']['start_host'])
    global END_HOST
    END_HOST = int(config['general']['end_host'])
    global GENERAL_CONFIG
    GENERAL_CONFIG = config['general']

    if '*' not in args.services:
        wanted_services = [s in args.services for s in found_services]
    else:
        wanted_services = found_services

    services = dict()
    for service in wanted_services:
        services[service] = config[service]

    if args.action == 'start':
        start(services, args.interface, args.netplanfile)
    elif args.action == 'stop':
        stop()


if __name__ == '__main__':
    main()
