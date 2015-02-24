
import sys, os, time
import subprocess, signal
import requests

from utils.discovery	import get_docker_ip

def test_slow_subscriber_breaks():
    mg2_ip	= get_docker_ip('mg2')
    url		= 'http://{0}/api'.format(mg2_ip)
    try:
        req	= requests.get(url, timeout=1)
        raise ValueError("Request was expected to timeout, but request was successful.")
    except ValueError as e:
        raise
    except Exception as e:
        pass

def test_slow_subscriber_passes():
    mg2_ip	= get_docker_ip('mg2')
    url		= 'http://{0}/api/ping?text=b5b44d95-2e33-4af9-95fe-1cade9cd86ef'.format(mg2_ip)
    for i in range(10):
        try:
            req		= requests.get(url, timeout=1)
            assert req.text == "b5b44d95-2e33-4af9-95fe-1cade9cd86ef"
            break
        except AssertionError as e:
            raise
        except Exception as e:
            print "Request timed out {0} times".format(i+1)
