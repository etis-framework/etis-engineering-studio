#!/usr/bin/env python3
"""Exercise the actual isolated simulator HTTP routes on an OS-assigned loopback port.

Standard library only. This does not call GitHub, Azure, or an AI reviewer, and
it does not assert browser/identity or real-student acceptance.
"""
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import Request, urlopen
import json
import student_ui_simulator as simulation


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),simulation.Handler)
    worker=Thread(target=server.serve_forever,daemon=True);worker.start()
    base=f'http://127.0.0.1:{server.server_port}'
    def get(route):
        with urlopen(base+route,timeout=5) as response:return response.status,response.read()
    def post(route):
        request=Request(base+route,method='POST',data=b'{}',headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=5) as response:return response.status,json.loads(response.read())
    try:
        status,markup=get('/')
        assert status==200 and b'Engineering Review Room' in markup and b'/simulation-controls.js' in markup
        _,controls=get('/simulation-controls.js');assert b'data-sim="older-newer"' in controls
        _,fixture=post('/__simulation/older-newer')
        assert (fixture['sessions'],fixture['snapshots'],fixture['commit'])==(2,2,'06ddeeff')
        _,latest=get('/api/v1/reviews/evidence/current?phase_id=A2')
        assert json.loads(latest)['snapshot_id']==82
        _,original=get('/api/v1/reviews/41')
        assert json.loads(original)['snapshot']['id']==81
        assert json.loads(original)['evidence']['commit_sha'].startswith('29aabbcc')
        _,fixture=post('/__simulation/long-conversation');assert fixture['sessions']==1
        _,old=get('/api/v1/reviews/41');assert len(json.loads(old)['turns'])==49
        _,fixture=post('/__simulation/fail-response');assert fixture['response_failure_queued']
        _,fixture=post('/__simulation/reset');assert fixture['sessions']==0
        print('PASS: loopback HTML, control JS, old/new snapshots, long transcript, failed-reply fixture, reset; zero external/model calls')
    finally:
        server.shutdown();server.server_close();worker.join(timeout=3)

if __name__=='__main__':main()
