import websocket
import json
import threading
import time
import requests
import time
import logging
import os
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

def get_dirname(file_path: str) -> Path:
  """
  Returns the directory canonical path of the file.

  Example:
  dirname = get_dirname(__file__)

  Parameters:
  file_path: File path
  """

  return Path(file_path).resolve().parent

dirname = get_dirname(__file__)
config_filename = 'config.yml'
default_username = 'MuiVP Bot'
default_avatar_url = 'https://cdn.discordapp.com/attachments/759302628940840980/920569746980753458/cute-robot-cat-vector-id1079767266.png'

logger.info("Program Started")
config_file_path = dirname / Path(config_filename)
if not config_file_path.exists():
  raise Exception(
      'Config file %s is missing. Please ensure it is created manually or by running setup.sh and adding the required fields.', config_filename)


def send_json_request(ws, request):
  ws.send(json.dumps(request))


def recieve_json_response(ws):
  response = ws.recv()
  if response:
    return json.loads(response)


def heartbeat(interval, ws):
  print('Hearbeat begin')
  while True:
    time.sleep(interval)
    heartbeatJSON = {
        "op": 1,
        "d": "null"
    }
    send_json_request(ws, heartbeatJSON)
    print("Heartbeat sent")


with open(config_file_path) as file:
  config = yaml.load(file, Loader=yaml.FullLoader)

  # Validate config file
  token = config.get('token')
  if not token:
    raise Exception('token is missing from the config file')
  webhooks = config.get('webhooks')
  if not webhooks:
    raise Exception('webhooks is missing from the config file')
  for webhook_name, webhook in webhooks.items():
    if not webhook.get('url'):
      raise Exception(f'webhook {webhook_name} is missing its url')

  try:
    ws = websocket.WebSocket()
    ws.connect('wss://gateway.discord.gg/?v=6&encoding=json')
    event = recieve_json_response(ws)

    heartbeat_interval = event['d']['heartbeat_interval'] / 1000
    threading._start_new_thread(heartbeat, (heartbeat_interval, ws))

    payload = {
        "op": 2,
        "d": {
            "token": token,
            "properties": {
                "$os": "windows",
                "$browser": "chrome",
                "$device": "pc"
            }
        }
    }
    send_json_request(ws, payload)

    def send_to_webhook(data):
        for webhook_name, webhook in config['webhooks'].items():
          data = {
              "username": webhook.get('username', default_username),
              "avatar_url": webhook.get('avatar_url', default_avatar_url),
              **data,
          }
          r = requests.post(webhook['url'], data=json.dumps(data), headers={'Content-Type': 'application/json'})

          logger.info('response: %s', r)


    filter_username = config['filter']['username']
    filter_role_id = config['filter']['role_id']

    while True:
      try:
        event = recieve_json_response(ws)

        try:
          if event['t'] == 'MESSAGE_CREATE':
            event_d = event['d']
            if event_d['author']['username'] == filter_username:
              logging.info("%s embed: %s", event_d['author']['username'], embeds)
              data = {
                'embeds': [
                  {
                      **(webhook.get('embed', {})),
                      **(embeds[0]),
                  },
                ]
              }
              send_to_webhook(data)

            if filter_role_id in event_d['mention_roles']:
              logging.info("%s content: %s", filter_role_id, content)
              content = content.replace(f'<@&{filter_role_id}>', '')
              data = {'content': content }
              send_to_webhook(data)

          op_code = event('op')

          if op_code == 11:
            print('heartbeat recieved')
        except Exception:
          pass
      except Exception:
        logging.exception("Error from recieve_json_response")
        break
  except Exception:
    logging.exception("Error while connecting using WS")

  time.sleep(5)
  print("Restarting program...")
  os.execv(sys.executable, ['python3'] + [sys.argv[0]])
