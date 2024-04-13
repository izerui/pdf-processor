import time
from subprocess import Popen, PIPE, STDOUT

import fitz

from support import a4_width, a4_height, logged


def test_html_to_pdf():
    s_time = int(time.perf_counter() * 1000)
    doc = fitz.open()
    page = doc.new_page(width=a4_width, height=a4_height)

    with open('dist/index.html', 'r') as f:
        content = f.read()
        page.insert_htmlbox(
            rect=page.rect,
            text=content
        )
    print(f'耗时: {int(time.perf_counter() * 1000) - s_time}/ms')
    doc.ez_save('x.pdf')


def exe_command(command):
    """
    执行 shell 命令并实时打印输出
    :param command: shell 命令
    :return: process, exitcode
    """
    print(command)
    process = Popen(command, stdout=PIPE, stderr=STDOUT, shell=True)
    with process.stdout:
        for line in iter(process.stdout.readline, b''):
            try:
                print(line.decode().strip())
            except:
                print(str(line))
    exitcode = process.wait()
    if exitcode != 0:
        print('错误: 命令执行失败, 继续下一条... ')
    return process, exitcode

def test_02():
    exe_command('wkhtmltopdf dist/index.html index.pdf')


def test_03():
    exe_command('wkhtmltopdf https://baidu.com baidu.pdf')
