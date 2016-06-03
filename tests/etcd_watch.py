import logging
import etcd
import time

from Queue import Queue
from threading import Thread


def process_queue(messages):
    logging.info("processing queue")

    while True:
        item = messages.get()
        logging.info("work done %s" % item)
        messages.task_done()


def main():
    client = etcd.Client()
    sleep_time = 3
    wait_index = 0
    message = None
    messages = Queue()

    # create a thread
    worker = Thread(target=process_queue, args=(messages,))
    worker.setDaemon(True)
    worker.start()

    while True:
        logging.info("watching on waitIndex %s" % wait_index)

        try:
            if wait_index:
                message = client.read('/nuage-gluon-test', recursive=True, wait=True, waitIndex=wait_index)

            else:
                message = client.read('/nuage-gluon-test', recursive=True, wait=True)

            messages.put(message.value)
            #logging.info("message received %s" % message.value)

        except KeyboardInterrupt:
            logging.info("exiting on interrupt")
            exit(1)

        except:
            pass

        #logging.info("sleeping for %s seconds" % sleep_time)
        #time.sleep(sleep_time)

        if (message.modifiedIndex - wait_index) > 1000:
            wait_index = 0

        else:
            wait_index = message.modifiedIndex + 1


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()