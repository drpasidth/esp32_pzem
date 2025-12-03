{
  "name": "IoT Electric with Alerts",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "iot-data",
        "responseMode": "responseNode",
        "options": {}
      },
      "id": "80362bf0-6658-4fbf-a233-5e3d0056838a",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [
        -544,
        112
      ],
      "webhookId": "iot-electric"
    },
    {
      "parameters": {
        "assignments": {
          "assignments": [
            {
              "id": "1",
              "name": "devid",
              "value": "={{ $json.body.devid }}",
              "type": "string"
            },
            {
              "id": "2",
              "name": "mcid",
              "value": "={{ $json.body.mcid }}",
              "type": "string"
            },
            {
              "id": "3",
              "name": "amp",
              "value": "={{ $json.body.current }}",
              "type": "number"
            },
            {
              "id": "4",
              "name": "volt",
              "value": "={{ $json.body.voltage }}",
              "type": "number"
            },
            {
              "id": "5",
              "name": "pf",
              "value": "={{ $json.body.pf }}",
              "type": "number"
            },
            {
              "id": "6",
              "name": "energy",
              "value": "={{ $json.body.energy }}",
              "type": "number"
            },
            {
              "id": "7",
              "name": "power",
              "value": "={{ $json.body.power }}",
              "type": "number"
            },
            {
              "id": "8",
              "name": "frequency",
              "value": "={{ $json.body.frequency }}",
              "type": "number"
            }
          ]
        },
        "options": {}
      },
      "id": "418162aa-b24f-4587-b821-d615cbf8cb7e",
      "name": "Extract Fields",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [
        -320,
        96
      ]
    },
    {
      "parameters": {
        "conditions": {
          "options": {
            "caseSensitive": true,
            "leftValue": "",
            "typeValidation": "strict"
          },
          "conditions": [
            {
              "id": "condition-current",
              "leftValue": "={{ $json.amp }}",
              "rightValue": 10,
              "operator": {
                "type": "number",
                "operation": "gt"
              }
            },
            {
              "id": "condition-voltage",
              "leftValue": "={{ $json.volt }}",
              "rightValue": 250,
              "operator": {
                "type": "number",
                "operation": "gt"
              }
            }
          ],
          "combinator": "or"
        },
        "options": {}
      },
      "id": "1c1a9c03-f49e-4b52-ad4a-7ec4d4db4566",
      "name": "Check Abnormal",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [
        -144,
        48
      ]
    },
    {
      "parameters": {
        "table": "electric",
        "dataMode": "defineBelow",
        "valuesToSend": {
          "values": [
            {
              "column": "devid",
              "value": "={{ $json.devid }}"
            },
            {
              "column": "mcid",
              "value": "={{ $json.mcid }}"
            },
            {
              "column": "amp",
              "value": "={{ $json.current }}"
            },
            {
              "column": "volt",
              "value": "={{ $json.voltage }}"
            },
            {
              "column": "pf",
              "value": "={{ $json.pf }}"
            },
            {
              "column": "energy",
              "value": "={{ $json.energy }}"
            }
          ]
        },
        "options": {}
      },
      "id": "b87be642-9061-45d8-8976-92de091a5b0d",
      "name": "MySQL (Normal)",
      "type": "n8n-nodes-base.mySql",
      "typeVersion": 2.4,
      "position": [
        96,
        -64
      ],
      "credentials": {
        "mySql": {
          "id": "Q0i4JbstLIa8z9lB",
          "name": "MySQL account"
        }
      }
    },
    {
      "parameters": {
        "chatId": "-4724666051",
        "text": "=⚠️ *IoT ALERT*\n\n*Device:* {{ $('Extract Fields').item.json.devid }}\n*Machine:* {{ $('Extract Fields').item.json.mcid }}\n\n🔴 *Current:* {{ $('Extract Fields').item.json.amp }} A\n🔴 *Voltage:* {{ $('Extract Fields').item.json.volt }} V\n⚡ *Power:* {{ $('Extract Fields').item.json.power }} W\n📊 *Energy:* {{ $('Extract Fields').item.json.energy }} kWh\n📈 *PF:* {{ $('Extract Fields').item.json.pf }}\n\n⏰ {{ $now.toISO() }}\n\n_Threshold: Current>10A or Voltage>250V_",
        "additionalFields": {
          "parse_mode": "Markdown"
        }
      },
      "id": "8a067eae-1812-451e-87ec-cf7b3b255bd6",
      "name": "Telegram Alert",
      "type": "n8n-nodes-base.telegram",
      "typeVersion": 1.2,
      "position": [
        304,
        128
      ],
      "webhookId": "ad9e86ce-c3a4-408b-88a4-6e0e3b0f3740",
      "credentials": {
        "telegramApi": {
          "id": "vUTYFmgxVnabjBwk",
          "name": "Telegram account"
        }
      }
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "={\"status\": \"OK\", \"message\": \"Data saved\"}",
        "options": {}
      },
      "id": "53d51b1f-d900-46c1-a7d7-f13c501eabe2",
      "name": "Respond OK",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [
        320,
        -64
      ]
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "={\"status\": \"ALERT\", \"message\": \"Abnormal detected, alerts sent\"}",
        "options": {}
      },
      "id": "68c7fa32-e3b3-423a-b367-73551136f333",
      "name": "Respond Alert",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [
        656,
        144
      ]
    },
    {
      "parameters": {
        "table": "electric",
        "dataMode": "defineBelow",
        "valuesToSend": {
          "values": [
            {
              "column": "devid",
              "value": "={{ $json.devid }}"
            },
            {
              "column": "mcid",
              "value": "={{ $json.mcid }}"
            },
            {
              "column": "amp",
              "value": "={{ $json.current }}"
            },
            {
              "column": "volt",
              "value": "={{ $json.voltage }}"
            },
            {
              "column": "pf",
              "value": "={{ $json.pf }}"
            },
            {
              "column": "energy",
              "value": "={{ $json.energy }}"
            }
          ]
        },
        "options": {}
      },
      "id": "5f178709-9347-426b-98f6-51c6db079ac4",
      "name": "MySQL (Normal)1",
      "type": "n8n-nodes-base.mySql",
      "typeVersion": 2.4,
      "position": [
        96,
        112
      ],
      "credentials": {
        "mySql": {
          "id": "Q0i4JbstLIa8z9lB",
          "name": "MySQL account"
        }
      }
    },
    {
      "parameters": {},
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1,
      "position": [
        -640,
        -96
      ],
      "id": "49d41abb-db14-435a-9720-5f073d0bed55",
      "name": "When clicking ‘Execute workflow’"
    },
    {
      "parameters": {
        "jsCode": "// Always generate alert condition for testing\nreturn [{\n  json: {\n    body: {\n      devid: \"ALERT-TEST\",\n      mcid: \"m-001\",\n      voltage: 265.5,    // > 250V - ALERT!\n      current: 15.2,     // > 10A - ALERT!\n      power: 4036.6,\n      energy: 2.45,\n      frequency: 50.0,\n      pf: 0.88\n    }\n  }\n}];"
      },
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [
        -464,
        -80
      ],
      "id": "c34c1a1c-554b-41ff-940d-cda85758f826",
      "name": "Code in JavaScript"
    },
    {
      "parameters": {
        "method": "POST",
        "url": "https://api.resend.com/emails",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Authorization",
              "value": "Bearer re_XYMtZ5o7_8mhCazrTft6yKg7C5ndnF7Ge"
            },
            {
              "name": "Content-Type",
              "value": "application/json"
            }
          ]
        },
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\n  \"from\": \"IoT Alert <onboarding@resend.dev>\",\n  \"to\": [\"psevolutionth@gmail.com\"],\n  \"subject\": \"⚠️ IoT ALERT: Abnormal from {{ $('Extract Fields').item.json.devid }}\",\n  \"html\": \"<h2 style='color:red;'>⚠️ Alert!</h2><p><b>Device:</b> {{ $('Extract Fields').item.json.devid }}</p><p><b>Current:</b> {{ $('Extract Fields').item.json.amp }} A</p><p><b>Voltage:</b> {{ $('Extract Fields').item.json.volt }} V</p><p><b>Power:</b> {{ $('Extract Fields').item.json.power }} W</p>\"\n}",
        "options": {}
      },
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.3,
      "position": [
        480,
        256
      ],
      "id": "4cc1337e-dc95-42b7-83f7-d6e29d800271",
      "name": "HTTP Request"
    }
  ],
  "pinData": {},
  "connections": {
    "Webhook": {
      "main": [
        [
          {
            "node": "Extract Fields",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Extract Fields": {
      "main": [
        [
          {
            "node": "Check Abnormal",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Check Abnormal": {
      "main": [
        [
          {
            "node": "MySQL (Normal)1",
            "type": "main",
            "index": 0
          }
        ],
        [
          {
            "node": "MySQL (Normal)",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "MySQL (Normal)": {
      "main": [
        [
          {
            "node": "Respond OK",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Telegram Alert": {
      "main": [
        [
          {
            "node": "HTTP Request",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "MySQL (Normal)1": {
      "main": [
        [
          {
            "node": "Telegram Alert",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "When clicking ‘Execute workflow’": {
      "main": [
        [
          {
            "node": "Code in JavaScript",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Code in JavaScript": {
      "main": [
        [
          {
            "node": "Extract Fields",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "HTTP Request": {
      "main": [
        [
          {
            "node": "Respond Alert",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "active": true,
  "settings": {
    "executionOrder": "v1"
  },
  "versionId": "f8bbde90-fac8-4182-9679-3afcc3c84e1c",
  "meta": {
    "templateCredsSetupCompleted": true,
    "instanceId": "9acb3c9bf0eb87970b4453d9ea6fd3a4299f471dbfd3112b967106023113d04c"
  },
  "id": "qmuSIjeM1I5SgegH",
  "tags": []
}
