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
                        "url": "https://file.yj2025.com/CH3600-1-M04003A%20搬运爪安装板-长.pdf",
                        "byte_array": "string",
                        "zoom": 1,
                        "marks": [
                            {
                                "x0": 0,
                                "y0": 0,
                                "x1": 200,
                                "y1": 300,
                                "image_url": "https://cdn.pixabay.com/photo/2023/11/09/19/36/zoo-8378189_1280.jpg"
                            }
                        ],
                        "rotations": [
                            0
                        ]
                    }
                ],
                "item_id": "当前请求的item的标识ID",
                "qr_code": "二维码内容",
                "doc_no": "卧室一个 DOC100",
                "inventory_code": "你以为的是 Ivne002，。",
                "inventory_name": "货品是 se名称！3",
                "inventory_spec": "货品规 *6ds格型号",
                "quantity": "数量 - 120",
                "doc_date": "2024年03月24日",
                "process_flow": "工艺路线1 》工艺路线 2"
            },
            {
                "files": [
                    {
                        "name": "单页.pdf",
                        "url": "https://tfile.yj2025.com/pdf-processor/source/2024-03-25/客户文件禁止外传.pdf",
                        "byte_array": "string",
                        "zoom": 1,
                        "marks": [
                            {
                                "x0": 0,
                                "y0": 0,
                                "x1": 200,
                                "y1": 300,
                                "image_url": "https://cdn.pixabay.com/photo/2023/11/09/19/36/zoo-8378189_1280.jpg"
                            }
                        ],
                        "rotations": [
                            0
                        ]
                    }
                ],
                "item_id": "当前请求的item的标识ID",
                "qr_code": "二维码内容",
                "doc_no": "卧室一个 DOC100",
                "inventory_code": "你以为的是 Ivne002，。",
                "inventory_name": "货品是 se名称！3",
                "inventory_spec": "货品规 *6ds格型号",
                "quantity": "数量 - 120",
                "doc_date": "2024年03月24日",
                "process_flow": "工艺路线1 》工艺路线 2"
            },
            {
                "files": [
                    {
                        "name": "单页.pdf",
                        "url": "https://file.yj2025.com/CH3600-1-M04003A%20搬运爪安装板-长.pdf",
                        "byte_array": "string",
                        "zoom": 1,
                        "marks": [
                            {
                                "x0": 0,
                                "y0": 0,
                                "x1": 200,
                                "y1": 300,
                                "image_url": "https://cdn.pixabay.com/photo/2023/11/09/19/36/zoo-8378189_1280.jpg"
                            }
                        ],
                        "rotations": [
                            0
                        ]
                    }
                ],
                "item_id": "当前请求的item的标识ID",
                "qr_code": "二维码内容",
                "doc_no": "卧室一个 DOC100",
                "inventory_code": "你以为的是 Ivne002，。",
                "inventory_name": "货品是 se名称！3",
                "inventory_spec": "货品规 *6ds格型号",
                "quantity": "数量 - 120",
                "doc_date": "2024年03月24日",
                "process_flow": "工艺路线1 》工艺路线 2"
            }, {
                "files": [
                    {
                        "name": "单页.pdf",
                        "url": "https://file.yj2025.com/CS01-P3-003.pdf",
                        "byte_array": "string",
                        "zoom": 1,
                        "marks": [
                            {
                                "x0": 0,
                                "y0": 0,
                                "x1": 200,
                                "y1": 300,
                                "image_url": "https://cdn.pixabay.com/photo/2023/11/09/19/36/zoo-8378189_1280.jpg"
                            }
                        ],
                        "rotations": [
                            0
                        ]
                    }
                ],
                "item_id": "当前请求的item的标识ID",
                "qr_code": "二维码内容",
                "doc_no": "卧室一个 DOC100",
                "inventory_code": "你以为的是 Ivne002，。",
                "inventory_name": "货品是 se名称！3",
                "inventory_spec": "货品规 *6ds格型号",
                "quantity": "数量 - 120",
                "doc_date": "2024年03月24日",
                "process_flow": "工艺路线1 》工艺路线 2"
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
