FROM python:3
ADD web_server.py /
ADD all /all
CMD [ "python", "./web_server.py" ]
RUN pip install -r requirements.txt