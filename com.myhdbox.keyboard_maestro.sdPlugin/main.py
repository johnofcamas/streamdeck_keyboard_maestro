#!/Users/johnsturgeon/Code/streamdeck_venv/bin/python

import argparse
import websocket
import json
from subprocess import Popen
from streamdeck_helpers import KMButtonInstance
from os.path import expanduser
import os


# Below are some configuration values that you should change before running
home = expanduser("~")
plugin_name = "streamdeck_keyboard_maestro"
# this should match the root folder where you installed the plugin
plugin_dir = f"{home}/Code/streamdeck/"
# Optional: Change this value to 'False' to disable logging
DEBUG = True
# Optional: Change this value to 'True' to truncate the log file on each run
TRUNCATE_LOGFILE = False
log_filename = f"{plugin_dir}/logs/{plugin_name}.log"


# create logs folder if none exists
if not os.path.exists(f"{plugin_dir}/logs"):
    os.makedirs(f"{plugin_dir}/logs")


parser = argparse.ArgumentParser(description='Streamdeck Plugin')
parser.add_argument('-port', dest='port')
parser.add_argument('-pluginUUID', dest='pluginUUID')
parser.add_argument('-registerEvent', dest='event')
parser.add_argument('-info', dest='info')
parser.add_argument('-propertyInspectorUUID', dest='propertyInspectorUUID')
args = parser.parse_args()

registration_dict = {'event': args.event, 'uuid': args.pluginUUID}
pi_registration_dict = {'event': args.event, 'uuid': args.propertyInspectorUUID}

instances = {}

# This will truncate the log file
if TRUNCATE_LOGFILE:
    t_log = open(log_filename, "w+")
    t_log.close()


def log_debug(message):
    if DEBUG:
        with open(log_filename, "a+") as log_file:
            log_file.write(f"{message}\n")


log_debug(args.port)
log_debug(args.pluginUUID)
log_debug(args.event)
log_debug(args.info)
log_debug(args.propertyInspectorUUID)


def on_message(ws, raw_message):
    global instances
    message = json.loads(raw_message)
    log_debug("\n\n== got message" + raw_message)
    event = message['event']
    payload = message['payload']
    context = message['context']
    instance = None

    if (event == 'willAppear'):
        try:
            log_debug("Got will appear")
            instance = KMButtonInstance(context)
            instance.settings = payload['settings']
            log_debug("[SETTINGS] Setting instance in dictionary")
            instances.update({context: instance})
        except Exception as e:
            log_debug(f"Exception {e}")

    else:
        log_debug(f"Getting instance from dictionary {instances}")
        instance = instances[context]

    log_debug(f"== Event: {event}")
    log_debug(f"== using Instance {instance}")
    log_debug(f"== with Context: {context}")
    if (event == 'keyUp'):
        Popen(['osascript', '-e', 'tell application "Keyboard Maestro Engine" to do script "' + instance.macroUUID() + '"'])

    if (event == 'sendToPlugin'):
        log_debug("got 'sendToPlugin' from javascript: Payload is:")
        log_debug(json.dumps(payload))
        if 'macroUUID' in payload:
            macroUUID = payload['macroUUID']
            save_settings_dict = {
                "event": "setSettings",
                "context": context,
                "payload": payload
            }
            log_debug("setting settings")
            log_debug("Sending the following to the server")
            log_debug(json.dumps(save_settings_dict))
            ws.send(json.dumps(save_settings_dict))
            log_debug("updating instance with macroUUID")
            instance.settings = {'macroUUID': macroUUID}

        if 'property_inspector' in payload:
            log_debug("Inspector has loaded")
            log_debug(f"instance is {instance}")
            log_debug(f"instance settings are: {instance.settings}")
            if (instance.macroUUID()) is None:
                log_debug("macroUUID is not set, not updating the inspector")
            else:
                log_debug(f"sending macroUUID to inspector using instance: {instance.macroUUID()}")
                send_to_pi_dict = {
                    "action": "com.elgato.example.action1",
                    "event": "sendToPropertyInspector",
                    "context": context,
                    "payload": {"macroUUID": instance.macroUUID()}
                }
                log_debug(json.dumps(send_to_pi_dict))
                ws.send(json.dumps(send_to_pi_dict))


def on_error(ws, error):
    log_debug(error)


def on_close(ws):
    log_debug("### closed ###")


def on_open(ws):
    global registration_dict
    global pi_registration_dict
    log_debug("### open ###")
    ws.send(json.dumps(registration_dict))
    ws.send(json.dumps(pi_registration_dict))


if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        'ws://localhost:' + args.port,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.on_open = on_open
    ws.run_forever()
