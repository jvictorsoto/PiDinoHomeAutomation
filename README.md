# PiDinoHomeAutomation

##Description

**PiDinoHomeAutomation** is an open source project under GNU license for HomeAutomation based on Raspberry pi & Arduino.

The main goal of the project is allow easy interaction between different home automation platforms and PiDino. Communication between modules is done over Modbus protocol, you can find more info about Modbus on [Wikipedia] (https://en.wikipedia.org/wiki/Modbus). Modbus can work over different transport layers, I'm currently using RS-485 in half-duplex mode (This mean than only 2 wires twisted plus ground is required, and usually, local ground is enough). RS-485 uses differential balanced lines, so it can span relatively large distances, up to 1,200 m (4,000 ft), offer high speeds (up to 100 mbps) and noise tolerance.

There are two types of modules, **master** and **slave**. All communication is started by the master module, each slave has an unique address and **16** of **16bits** local registers. The master module can either read or write on slaves registers. 

##Modules

Currently this modules are implemented, the type of the module (master/slave) is denoted in its name.


###RestServer-master

This module, written in Python, offers a REST API with **json** as body language to interact with all of the slaves.

**Dependencies**

Can be installed easily from pip

```
pip install flask minimalmodbus
```

**Usage**

```
Usage: pidino_server.py [options]

Options:
  -h, --help            show this help message and exit
  -c CONF, --config=CONF
                        Use another config file.
  -d DEVS, --devices=DEVS
                        Use another devices file.
  -v, --verbose         Show all logging to stdout.
  --logLevel=LOG_LEVEL  Set the logger level.
```


There are two configuration files:

**Server config**

This file controls the basic server functionality and has two sections, Basic and TrustedProxies.

```
[Basic]
Host:       0.0.0.0
Port:       5001
LogFile:    pidino.log
# 200MB in bytes, 200*1024*1024
LogMaxSize: 209715200

[TrustedProxies]
Enabled: True
Allowed: ["127.0.0.1"]
```

**Devices config**

This file list the different devices, its configuration and its registers with read/write permissions.

```
[heater]
Interface: /dev/ttyUSB0
BaudRate:  19200
ByteSize:  8
Parity:    NONE
StopBits:  1
Timeout:   0.05
Mode:      RTU
Address:   1
Registers: [{"read": true, "write": true}, 
            {"read": true, "write": true}, 
            {"read": true, "write": true}, 
            {"read": true, "write": true}]

[cooler]
Interface: /dev/ttyUSB0
BaudRate:  19200
ByteSize:  8
Parity:    NONE
StopBits:  1
Timeout:   0.05
Mode:      RTU
Address:   2
Registers: [{"read": true, "write": true}]
```

Current API specification (variables are denoted between %):

Path | Method | Status Code | Body
---------- | ------------- | ------------- | -------------
/%deviceName%/registers/%registerId% | GET | 200 | {"value": %registerValue%}
||| 400 | {"msg": "Device %deviceName% not found, check your devices config file"}
||| 401 | {"msg": "You are not authorized."}
||| 403 | {"msg": "You dont have permission to do that."}
||| 404 | {"msg": "Register %registerId% out of index. Device %deviceName% has only %deviceRegisters% registers"}
||| 500 | {"msg": "Error trying to read register value. Something went wrong, check server log"}                                                                      
/%deviceName%/registers/%registerId% | POST, PUT | 200 | {"msg": "register updated successfully"}
||| 400 | {"msg": "Device %deviceName% not found, check your devices config file"}
||| 401 | {"msg": "You are not authorized."}
||| 403 | {"msg": "You dont have permission to do that."}
||| 404 | {"msg": "Register %registerId% out of index. Device %deviceName% has only %deviceRegisters% registers"}
||| 500 | {"msg": "Error trying to write register value. Something went wrong, check server log"} 

