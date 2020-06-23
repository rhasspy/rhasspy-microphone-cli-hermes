# Rhasspy Microphone Hermes MQTT Service

[![Continous Integration](https://github.com/rhasspy/rhasspy-microphone-cli-hermes/workflows/Tests/badge.svg)](https://github.com/rhasspy/rhasspy-microphone-cli-hermes/actions)
[![GitHub license](https://img.shields.io/github/license/rhasspy/rhasspy-microphone-cli-hermes.svg)](https://github.com/rhasspy/rhasspy-microphone-cli-hermes/blob/master/LICENSE)

Records audio from an external program and publishes WAV chunks according to the [Hermes protocol](https://docs.snips.ai/reference/hermes).

## Requirements

* Python 3.7

## Installation

```bash
$ git clone https://github.com/rhasspy/rhasspy-microphone-cli-hermes
$ cd rhasspy-microphone-cli-hermes
$ ./configure
$ make
$ make install
```

## Deployment

```bash
$ make dist
```

## Running

```bash
$ bin/rhasspy-microphone-cli-hermes <ARGS>
```

## Command-Line Options

```
usage: rhasspy-microphone-cli-hermes [-h] --record-command RECORD_COMMAND
                                     --sample-rate SAMPLE_RATE --sample-width
                                     SAMPLE_WIDTH --channels CHANNELS
                                     [--list-command LIST_COMMAND]
                                     [--test-command TEST_COMMAND]
                                     [--output-site-id OUTPUT_SITE_ID]
                                     [--udp-audio-host UDP_AUDIO_HOST]
                                     [--udp-audio-port UDP_AUDIO_PORT]
                                     [--host HOST] [--port PORT]
                                     [--username USERNAME]
                                     [--password PASSWORD] [--tls]
                                     [--tls-ca-certs TLS_CA_CERTS]
                                     [--tls-certfile TLS_CERTFILE]
                                     [--tls-keyfile TLS_KEYFILE]
                                     [--tls-cert-reqs {CERT_REQUIRED,CERT_OPTIONAL,CERT_NONE}]
                                     [--tls-version TLS_VERSION]
                                     [--tls-ciphers TLS_CIPHERS]
                                     [--site-id SITE_ID] [--debug]
                                     [--log-format LOG_FORMAT]

optional arguments:
  -h, --help            show this help message and exit
  --record-command RECORD_COMMAND
                        Command to record raw audio data
  --sample-rate SAMPLE_RATE
                        Sample rate of recorded audio in hertz (e.g., 16000)
  --sample-width SAMPLE_WIDTH
                        Sample width of recorded audio in bytes (e.g., 2)
  --channels CHANNELS   Number of channels in recorded audio (e.g., 1)
  --list-command LIST_COMMAND
                        Command to list available microphones
  --test-command TEST_COMMAND
                        Command to test a specific microphone
  --output-site-id OUTPUT_SITE_ID
                        If set, output audio data to a different site_id
  --udp-audio-host UDP_AUDIO_HOST
                        Host for UDP audio (default: 127.0.0.1)
  --udp-audio-port UDP_AUDIO_PORT
                        Send raw audio to UDP port outside ASR listening
  --host HOST           MQTT host (default: localhost)
  --port PORT           MQTT port (default: 1883)
  --username USERNAME   MQTT username
  --password PASSWORD   MQTT password
  --tls                 Enable MQTT TLS
  --tls-ca-certs TLS_CA_CERTS
                        MQTT TLS Certificate Authority certificate files
  --tls-certfile TLS_CERTFILE
                        MQTT TLS certificate file (PEM)
  --tls-keyfile TLS_KEYFILE
                        MQTT TLS key file (PEM)
  --tls-cert-reqs {CERT_REQUIRED,CERT_OPTIONAL,CERT_NONE}
                        MQTT TLS certificate requirements (default:
                        CERT_REQUIRED)
  --tls-version TLS_VERSION
                        MQTT TLS version (default: highest)
  --tls-ciphers TLS_CIPHERS
                        MQTT TLS ciphers to use
  --site-id SITE_ID     Hermes site id(s) to listen for (default: all)
  --debug               Print DEBUG messages to the console
  --log-format LOG_FORMAT
                        Python logger format
```
