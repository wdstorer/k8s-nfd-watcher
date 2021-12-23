FROM python:latest
RUN pip install requests pyyaml
COPY main.py /main.py
COPY config /config
ENTRYPOINT [ "python", "/main.py" ]