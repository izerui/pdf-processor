FROM harbor.yj2025.com/library/python:3.10.13-slim

#RUN export https_proxy=http://192.168.1.39:7890 http_proxy=http://192.168.1.39:7890 all_proxy=socks5://192.168.1.39:7890
#RUN apt update
#RUN apt-get install ttf-wqy-zenhei
#RUN unset http_proxy
#RUN unset https_proxy
#RUN unset all_proxy

WORKDIR /data

RUN pip config set global.index-url https://mirror.baidu.com/pypi/simple/
RUN pip install PyMuPDF==1.24.5 qrcode fastapi[all] uvicorn[standard]
RUN pip install fonttools
RUN pip install tqdm
RUN pip install qiniu
RUN pip install psutil
RUN pip install Pillow
RUN pip install prettytable

COPY *.py ./
COPY ./model/ ./model/
COPY ./pdf/ ./pdf/
COPY ./support/ ./support/
#COPY ./tests/ ./tests/
COPY ./view/ ./view/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--timeout-keep-alive", "60", "--workers", "8"]