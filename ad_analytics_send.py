# coding: utf-8

import json
import requests
import datetime
import base64
import mimetypes
from pprint import pprint
from email.mime.text import MIMEText
from email.utils import formatdate
from email.header import Header

class GAPI:
  def __init__(self):
    with open('./client_secret.json') as f:
      self.param = json.load(f)['param']

  # update the access token by the refresh token
  def get_access_token(self):
    payload = {
      'client_id': self.param['client_id'],
      'client_secret': self.param['client_secret'],
      'redirect_uri': self.param['redirect_uris'],
      'grant_type': 'refresh_token',
      'refresh_token': self.param['refresh_token']
    }
    
    r = requests.post(self.param['token_uri'], data=payload)
    self.param['access_token'] = r.json()['access_token']

    return self.param['access_token']

  def get_adsense_info(self):
    return self.param['adsense_id']

  def get_analytics_info(self):
    return self.param['analytics_id']

  def get_mail_info(self):
    return {"mail_from": self.param['mail_from'], "mail_to": self.param['mail_to']}
    
      
if __name__ == '__main__':
  gapi = GAPI()
  access_token = gapi.get_access_token()

  mail_body = {}

  # fetch adsense info
  accountId = gapi.get_adsense_info()
  ads_endpoint_report = 'https://www.googleapis.com/adsense/v1.4/accounts/' + accountId + '/reports'
  today = datetime.date.today()

  headers = { 'Authorization': 'Bearer ' + access_token } 
  params = {
    'startDate': today - datetime.timedelta(days=1),
    'endDate': today - datetime.timedelta(days=1),
    'metric': ['CLICKS', 'EARNINGS', 'PAGE_VIEWS_RPM']
  }

  r = requests.get(ads_endpoint_report, params=params, headers=headers)
  mail_body["adsense"] = r.json()["rows"][0]

  # fetch analytics info
  analytics_view_id = gapi.get_analytics_info()
  analytics_endpoint_report = 'https://analyticsreporting.googleapis.com/v4/reports:batchGet'

  headers.update({'Content-type': 'application/json'})
  
  payload = {
    "reportRequests": [
      {
        "viewId": analytics_view_id,
        "dateRanges": [
          {
            "startDate": str(today - datetime.timedelta(days=1)),
            "endDate": str(today - datetime.timedelta(days=1))
          }
        ],
        "metrics": [
          {
            "expression": "ga:pageviews"
          }
        ]
      }
    ]
  }

  r = requests.post(analytics_endpoint_report, data=json.dumps(payload), headers=headers)
  mail_body["analytics"] = r.json()["reports"][0]["data"]["maximums"][0]["values"][0]


  mail_info = gapi.get_mail_info()
  
  userId = mail_info["mail_from"]
  gmail_endpoint_send = "https://www.googleapis.com/gmail/v1/users/" + userId + "/messages/send"
  MAIL_TO = mail_info["mail_to"]
  MAIL_FROM = userId

  msg_body = "PV: %s\n" % mail_body["analytics"]
  msg_body += "CLICK: %s  EARN: %s Yen  RPM: %s Yen" % (mail_body["adsense"][0], mail_body["adsense"][1], mail_body["adsense"][2])

  msg = MIMEText(msg_body)
  msg['to'] = MAIL_TO
  msg['from'] = MAIL_FROM
  msg['subject'] = Header("Daily report", "utf-8")

  b64_msg = base64.urlsafe_b64encode(msg.as_string().encode(encoding='utf-8'))
  s64_msg = b64_msg.decode(encoding='utf-8')

  msg = {"raw": s64_msg}

  r = requests.post(gmail_endpoint_send, data=json.dumps(msg), headers=headers)

