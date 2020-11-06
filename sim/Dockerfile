FROM ubuntu:latest

RUN echo 'Acquire::http { Proxy "http://10.50.50.5:3142"; };' >> /etc/apt/apt.conf.d/00aptproxy

RUN apt-get update && \
    apt-get -y install git python python-dbus python-gobject python-pip

COPY . /sim
WORKDIR /sim
RUN pip install -r requirements.txt

ENTRYPOINT python -i run.py -c default_config.yml -v 2
