import threading
from http import client
import json
import datetime
import sys

host = "stats.foldingathome.org"
project_url_template = "/project?p=%(id)s&format=text&version=7.6"
team_url_template = "/api/team/%(id)s"


class CachingHTTPClient:

    def __init__(self, url_template, response_parser):
        self.cache = {}
        self.fetching = {}
        self.pending_callbacks = {}
        self.lock = threading.RLock()
        self.url_template = url_template
        self.response_parser = response_parser
        self.instance_created_at = datetime.datetime.now()

    @staticmethod
    def decode(bytes):
        try:
            return bytes.decode("utf-8")
        except UnicodeDecodeError:
            print("Wrong unicode: attempting decoding using latin1", file=sys.stderr)
            return bytes.decode("latin1")

    def _fetch(self, id):
        try:
            http_connection = client.HTTPSConnection(host, timeout=5)
            http_connection.request("GET", self.url_template % {"id": id})
            response = http_connection.getresponse()
            if response.status != 200:
                return

            body_bytes = response.read()
            body = self.decode(body_bytes)
            item = self.response_parser(body)
            with self.lock:
                self.cache[id] = item
                del self.fetching[id]
                callbacks = self.pending_callbacks[id].copy()
                self.pending_callbacks[id].clear()

            for callback in callbacks:
                callback(id, item)
        except Exception as e:
            with self.lock:
                del self.fetching[id]
                self.pending_callbacks[id].clear()

    def get(self, id, callback):
        if id is None:
            return

        with self.lock:
            if id in self.cache:
                callback(id, self.cache[id])
                return

            if id in self.fetching:
                return

            if id not in self.pending_callbacks:
                self.pending_callbacks[id] = []
            self.pending_callbacks[id].append(callback)

            thread = threading.Thread(target=self._fetch, args=[id], daemon=True)
            self.fetching[id] = thread
            thread.start()

            return


MAX_PROJECT_DESCRIPTION_LENGTH = 400 - len("...")  # see webcontrol source code


class ProjectFetcher:

    def __init__(self):
        self.http_client = CachingHTTPClient(project_url_template, self.response_parser)

    def get(self, id, callback):
        if id == 0:
            callback(id, "")
            return

        self.http_client.get(id, callback)

    @staticmethod
    def response_parser(body):
        project_description = body.split("\n")[6:]
        list_of_contributors_idx = [i for i, x in enumerate(project_description) if
                                    x.lower().startswith("list of contributors")]
        if len(list_of_contributors_idx) > 0:
            project_description = project_description[0:list_of_contributors_idx[0]]

        project_description = [row for row in project_description if row != ""]
        project_description = "\n".join(project_description)
        if len(project_description) > MAX_PROJECT_DESCRIPTION_LENGTH:
            project_description = project_description[0:MAX_PROJECT_DESCRIPTION_LENGTH] + "..."

        return project_description


class TeamFetcher:

    def __init__(self):
        self.http_client = CachingHTTPClient(team_url_template, self.response_parser)
        self.get = self.http_client.get

    @staticmethod
    def response_parser(body):
        return json.loads(body)


if __name__ == '__main__':
    import time


    def p1(res):
        print('t1', res)


    def p2(team):
        print('t2', len(team['donors']))


    t = ProjectFetcher()
    t.get(14800, p1)
    print('waiting')
    time.sleep(10)
