import logging
import etcd
import sys, time


def main():
    client = etcd.Client()
    sleep_time = 1
    i = 0

    while True:
        value = 'hello word ' + str(i)
        logging.info("writing %s" % value)
        message = client.write('/nuage-gluon-test', value)
        logging.info("sleeping for %s seconds" % sleep_time)
        i=i+1
        time.sleep(sleep_time)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()