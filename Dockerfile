FROM harbor.yj2025.com/library/python3:3.10-debian-12

#RUN export https_proxy=http://192.168.1.39:7890 http_proxy=http://192.168.1.39:7890 all_proxy=socks5://192.168.1.39:7890
#RUN apt update
#RUN apt-get install ttf-wqy-zenhei
#RUN unset http_proxy
#RUN unset https_proxy
#RUN unset all_proxy

WORKDIR /data

RUN pip config set global.index-url https://mirrors.cloud.tencent.com/pypi/simple/
RUN pip install PyMuPDF==1.24.5
RUN pip install fastapi[all]==0.110.0
RUN pip install qrcode==7.4.2
RUN pip install uvicorn[standard]==0.29.0
RUN pip install fonttools==4.50.0
RUN pip install tqdm==4.66.2
RUN pip install qiniu==7.13.1
RUN pip install psutil==5.9.8
RUN pip install Pillow==10.2.0
RUN pip install prettytable==3.10.0

COPY *.py ./
COPY ./model/ ./model/
COPY ./pdf/ ./pdf/
COPY ./support/ ./support/
#COPY ./tests/ ./tests/
COPY ./view/ ./view/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--timeout-keep-alive", "60", "--workers", "8"]