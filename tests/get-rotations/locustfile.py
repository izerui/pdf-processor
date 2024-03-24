import logging
import os

from locust import task, TaskSet, HttpUser, between


class TestAsync(TaskSet):

    # 执行并发前置动作
    def on_start(self):
        # logging.info('压测开始！！！')
        pass

    # 压测任务，也可以是@task(10)啥的，这个数字是代表权重,数值越大,执行的频率就越高
    @task(10)
    def ratations(self):
        url = '/rotations/from-urls'
        data = [
            {
                "name": "我的世界.pdf",
                "url": "https://file.yj2025.com/CS01-P3-003.pdf"
            }
        ]
        header = {"Content-Type": "application/json;charset=UTF-8"}
        response = self.client.request(method='POST', url=url, json=data, headers=header, name='测试获取旋转角度',
                                       verify=False,
                                       allow_redirects=False)
        self.result = response.content

    # 执行并发测试后执行的动作，查看报告http://localhost:8089/
    def on_stop(self):
        logging.info(f'{self.result}')


class Config(HttpUser):
    host = 'http://127.0.0.1:8000'
    # 每次请求停顿时间
    # wait_time = between(1, 3)
    tasks = [TestAsync]


if __name__ == "__main__":
    print("打开并开始任务: http://localhost:8089/")
    os.system("locust")
