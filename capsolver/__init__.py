import aiohttp
from app import config


class Api:
    def __init__(self, session=None):
        self.api_url = 'https://api.capsolver.com'
        self.type = 'AntiTurnstileTaskProxyLess'
        self.api_key = config.CAPSOLVER_API_KEY
        self.website_url = config.SERVICE_TURNSTILE_URL
        self.website_key = config.SERVICE_TURNSTILE_TOKEN
        self.task_id = None
        self.success = True
        self.error = None
        self.result = None
        self.session = session or aiohttp.ClientSession()

    def handle_response(self, res):
        if res['errorId'] != 0:
            self.success = False
            self.error = res['errorCode']

    async def create_task(self):
        data = {
            'clientKey': self.api_key,
            'task': {
                'type': self.type,
                'websiteURL': self.website_url,
                'websiteKey': self.website_key
            }
        }
        res = await self.session.post(self.api_url + '/createTask', json=data, timeout=10)
        res = await res.json()
        print(res)
        self.handle_response(res)
        if self.success:
            self.task_id = res['taskId']

    async def check_task(self):
        data = {
            'clientKey': self.api_key,
            'taskId': self.task_id
        }
        res = await self.session.post(self.api_url + '/getTaskResult', json=data, timeout=10)
        res = await res.json()
        self.handle_response(res)
        if not self.success:
            return
        if res['status'] == 'ready':
            self.result = res['solution']['token']
