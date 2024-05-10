FROM python:3.10.13-slim

# RUN cp -pv /etc/apt/sources.list /etc/apt/sources.list.bak
# RUN sed -i -e 's/deb.debian.org/mirrors.ustc.edu.cn/g' -e 's/security.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list
# RUN apt update
# RUN apt-get update && apt-get install -y --no-install-recommends libgl1-mesa-glx
# RUN apt-get install -y libglib2.0-dev libgomp1
RUN apt-get install ttf-wqy-zenhei

WORKDIR /data

RUN pip config set global.index-url https://mirror.baidu.com/pypi/simple/
RUN pip install PyMuPDF==1.24.2 qrcode fastapi[all] uvicorn[standard]
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

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--timeout-keep-alive", "60", "--workers", "16"]