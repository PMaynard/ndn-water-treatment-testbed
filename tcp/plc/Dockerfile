FROM ubuntu:latest

RUN echo 'Acquire::http { Proxy "http://10.50.50.5:3142"; };' >> /etc/apt/apt.conf.d/00aptproxy

RUN apt-get update && \
    apt-get -y install git build-essential python python-dbus python-gobject python-pip libssl-dev libffi-dev

COPY . /scadasim-plc

WORKDIR /scadasim-plc

RUN pip install -r requirements.txt

EXPOSE 502

ENTRYPOINT python scadasim_plc/plc.py
