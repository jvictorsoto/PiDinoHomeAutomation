#!/bin/python
"""

PyDino HomeAutomation Master Server
Author: J. Victor Soto
Version: 0.1
Date(YYYYMMDD): 20160310

Description: This is the master module for PyDino HomeAutomation project, it will offer a HTTP endpoint for REST
             json encoded request that will be translated into Modbus operations over slaves.
             This system support a random number of Modbus interfaces and a random number of slaves, but, usually
             hardware don't, so check how many slaves can hold your setup (usually 256 each interface).

Config Files: The server will use two config file, one for server related configuration and other for slave listing

"""

import optparse
import ConfigParser
import logging
import json
import minimalmodbus
import serial
from flask import Flask, jsonify, request


# Get logger
log_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] - %(message)s")
logger = logging.getLogger()

# Global server variables
config = {}
devices = {}
instruments = {}

# Flask server object
app = Flask(__name__)


# Flask helper to abort requests
def flask_abort(status_code, data):
    response = jsonify(data)
    response.status_code = status_code
    return response


# Flask Routes
@app.route('/<slave>/registers/<int:register>', methods=['GET'])
def read_register(slave, register):
    global instruments, devices
    if slave not in instruments or slave not in devices:
        return flask_abort(404, {'msg': 'Device %s not found, check your devices config file' % slave})

    if register > len(devices[slave]['registers']) - 1:
        return flask_abort(400, {'msg': 'Register %d out of index. Device %s has only %d registers'
                                 % (register, slave, len(devices[slave]['registers']))})

    register_value = None
    decimals = request.args.get('decimals') or 0
    try:
        register_value = instruments[slave].read_register(register, int(decimals))
    except Exception as e:
        logger.error("Trying to get register %d value of device: %s. Error: %s" % (register, slave, str(e)))

    if register_value is None:
        return flask_abort(500, {'msg': 'Error trying to read register value. Something went wrong, check server log'})

    return jsonify({'value': register_value})


@app.route('/<slave>/registers/<int:register>', methods=['POST', 'PUT'])
def write_register(slave, register):
    global instruments, devices

    if not request.json or 'value' not in request.json:
        return flask_abort(400, {'msg': 'No value in body!'})

    if type(request.json['value']) is not int or request.json['value'] < 0 or request.json['value'] > 65535:
        return flask_abort(400, {'msg': 'Invalid value: %s, must be a 16 bit unsigned integer!'
                                        % request.json['value']})

    if slave not in instruments or slave not in devices:
        return flask_abort(404, {'msg': 'Device %s not found, check your devices config file' % slave})

    if register > len(devices[slave]['registers']) - 1:
        return flask_abort(400, {'msg': 'Register %d out of index. Device %s has only %d registers'
                                 % (register, slave, len(devices[slave]['registers']))})

    try:
        instruments[slave].write_register(register, request.json['value'], 0)
    except Exception as e:
        logger.error("Trying to get register %d value of device: %s. Error: %s" % (register, slave, str(e)))
        return flask_abort(500, {'msg': 'Error trying to write register value. Something went wrong, check server log'})

    return jsonify({'msg': 'register updated successfully'})


# Config parsers
def read_config_file(path):
    parser = ConfigParser.ConfigParser()
    parser.read(path)

    config_content = {
        'basic': {
            'host': parser.get('Basic', 'Host'),
            'port': parser.get('Basic', 'Port'),
            'log_file': parser.get('Basic', 'LogFile'),
            'log_max_size': int(parser.get('Basic', 'LogMaxSize')),
        },
        'trusted_proxies': {
            'enabled': parser.getboolean('TrustedProxies', 'Enabled'),
            'allowed': json.loads(parser.get('TrustedProxies', 'Allowed'))
        }
    }

    return config_content


def read_devices_file(path):
    parser = ConfigParser.ConfigParser()
    parser.read(path)

    devices_content = {}

    for device in parser.sections():
        minimal_modbus_mode = minimalmodbus.MODE_RTU
        if parser.get(device, 'Mode') == 'ASCII':
            minimal_modbus_mode = minimalmodbus.MODE_ASCII
        elif parser.get(device, 'Mode') != 'RTU':
            print("Unsupported mode: %s for device %s. Options are RTU or ASCII."
                  % (device, parser.get(device, 'Mode')))
            exit(1)

        serial_parity = serial.PARITY_NONE
        if parser.get(device, 'Parity') == 'EVEN':
            serial_parity = serial.PARITY_EVEN
        elif parser.get(device, 'Parity') == 'ODD':
            serial_parity = serial.PARITY_ODD
        elif parser.get(device, 'Parity') != 'NONE':
            print("Unsupported parity mode: %s for device %s. Options are NONE, ODD or EVEN."
                  % (device, parser.get(device, 'Parity')))
            exit(1)

        devices_content[device] = {
            'interface': parser.get(device, 'Interface'),
            'baud_rate': int(parser.get(device, 'BaudRate')),
            'byte_size': int(parser.get(device, 'ByteSize')),
            'parity': serial_parity,
            'stop_bits': int(parser.get(device, 'StopBits')),
            'timeout': float(parser.get(device, 'Timeout')),
            'mode': minimal_modbus_mode,
            'address': int(parser.get(device, 'Address')),
            'registers': json.loads(parser.get(device, 'Registers')),
        }

    # TODO: Safe check, do not allow devices with same interface & address
    return devices_content


def main():
    cli = optparse.OptionParser()
    cli.add_option("-c", "--config", dest="conf", default="config.cfg", help="Use another config file.")
    cli.add_option("-d", "--devices", dest="devs", default="devices.cfg", help="Use another devices file.")
    cli.add_option("-v", "--verbose", dest="verbose", action="store_true", default=False,
                   help="Show all logging to stdout.")
    cli.add_option("--logLevel", dest="log_level", default="INFO", help="Set the logger level.")
    opt, _ = cli.parse_args()

    if opt.log_level not in ['DEBUG', 'INFO', 'WARN', 'ERROR']:
        print("%s is not a valid logger level, valid options are: 'DEBUG', 'INFO', 'WARN', 'ERROR'" % opt.log_level)
        exit(1)

    logger.setLevel(opt.log_level)

    if opt.verbose:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)

    global config, devices, instruments
    config = read_config_file(opt.conf)
    devices = read_devices_file(opt.devs)
    instruments = {}

    file_handler = logging.FileHandler(config['basic']['log_file'])
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    # Setup instruments
    for device in devices:
        try:
            instruments[device] = minimalmodbus.Instrument(devices[device]['interface'], devices[device]['address'],
                                                           devices[device]['mode'])
            instruments[device].serial.baudrate = devices[device]['baud_rate']
            instruments[device].serial.bytesize = devices[device]['byte_size']
            instruments[device].serial.parity = serial.PARITY_NONE
            instruments[device].serial.stopbits = devices[device]['stop_bits']
            instruments[device].serial.timeout = devices[device]['timeout']
            logger.info("Instrument for device: %s at %s with address %d ready"
                        % (device, devices[device]['interface'], devices[device]['address']))
        except Exception as e:
            logger.error("Setting up modbus instrument for device: %s. Exception: %s" % (device, str(e)))
            exit(1)

    logger.info("Starting flask rest server...")
    app.run(host=config['basic']['host'], port=config['basic']['port'])


if __name__ == '__main__':
    main()
