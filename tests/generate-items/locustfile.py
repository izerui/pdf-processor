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
        url = '/generate/from-urls'
        data = [
            {
                "files": [
                    {
                        "name": "单页.pdf",
                        "url": "https://file.yj2025.com/003.pdf",
                        "byte_array": "string",
                        "zoom": 1,
                        "marks": [
                        ],
                        "rotations": [
                            0
                        ]
                    }
                ],
                "item_id": "string",
                "qr_code": "string",
                "doc_no": "string",
                "inventory_code": "string",
                "inventory_name": "string",
                "inventory_spec": "string",
                "quantity": "string",
                "doc_date": "string",
                "process_flow": "string"
            },
            {
                "files": [
                    {
                        "name": "单页.pdf",
                        "url": "https://file.yj2025.com/003.pdf",
                        "byte_array": "string",
                        "zoom": 1,
                        "marks": [
                        ],
                        "rotations": [
                            0
                        ]
                    }
                ],
                "item_id": "string",
                "qr_code": "string",
                "doc_no": "string",
                "inventory_code": "string",
                "inventory_name": "string",
                "inventory_spec": "string",
                "quantity": "string",
                "doc_date": "string",
                "process_flow": "string"
            },
            {
                "files": [
                    {
                        "name": "单页.pdf",
                        "url": "https://file.yj2025.com/003.pdf",
                        "byte_array": "string",
                        "zoom": 1,
                        "marks": [
                        ],
                        "rotations": [
                            0
                        ]
                    }
                ],
                "item_id": "string",
                "qr_code": "string",
                "doc_no": "string",
                "inventory_code": "string",
                "inventory_name": "string",
                "inventory_spec": "string",
                "quantity": "string",
                "doc_date": "string",
                "process_flow": "string"
            },
            {
                "files": [
                    {
                        "name": "单页.pdf",
                        "url": "https://file.yj2025.com/003.pdf",
                        "byte_array": "string",
                        "zoom": 1,
                        "marks": [
                        ],
                        "rotations": [
                            0
                        ]
                    }
                ],
                "item_id": "string",
                "qr_code": "string",
                "doc_no": "string",
                "inventory_code": "string",
                "inventory_name": "string",
                "inventory_spec": "string",
                "quantity": "string",
                "doc_date": "string",
                "process_flow": "string"
            }
        ]
        header = {"Content-Type": "application/json;charset=UTF-8"}
        response = self.client.request(method='POST', url=url, json=data, headers=header, name='根据items批量处理PDF',
                                       verify=False,
                                       allow_redirects=False)
        # self.result = response.content

    # 执行并发测试后执行的动作，查看报告http://localhost:8089/
    def on_stop(self):
        # logging.info(f'{self.result}')
        pass


class Config(HttpUser):
    host = 'http://127.0.0.1:8000'
    # 每次请求停顿时间
    # wait_time = between(1, 3)
    tasks = [TestAsync]


if __name__ == "__main__":
    print("打开并开始任务: http://localhost:8089/")
    os.system("locust")
