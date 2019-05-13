import socket
import sys
import requests
import requests_oauthlib
import json
import pykafka
import pickle
from afinn import Afinn

# Replace the values below with yours
ACCESS_TOKEN = '4431903384-sV7w5hZtiBxmqskOFwqYcxUflT1RXk9fEktc2ZV'
ACCESS_SECRET = 'TtJ13XEjs76GOWuNHFtwlhxAB5Xhk0jrN8AEJxgrlyA5y'
CONSUMER_KEY = 'ljMnhmniWdVGyf7IAtJQIVKZi'
CONSUMER_SECRET = 'XsMXXWdt7W2iLRMlargBN4CC5ULQXCIYcLnuKgiHMuLgJwQYg2'
my_auth = requests_oauthlib.OAuth1(CONSUMER_KEY, CONSUMER_SECRET,ACCESS_TOKEN, ACCESS_SECRET)


def send_tweets_to_spark(http_resp, tcp_connection):
    for line in http_resp.iter_lines():
        try:
            full_tweet = json.loads(line)

            send_data = '{}'
            my_data = json.loads(send_data)

            my_data['text'] = full_tweet['text'].rstrip("\n")
            my_data['senti_val'] = afinn.score(full_tweet['text'])

            tweet = str(my_data['text']) + '\n' + str(my_data['senti_val']) + '\n'

            tweet_text = full_tweet['text']
            print("Tweet Text: " + tweet_text)
            print ("------------------------------------------")
            tcp_connection.send(tweet)
        except:
            e = sys.exc_info()[0]
            print("Error: %s" % e)


def get_tweets():
    url = 'https://stream.twitter.com/1.1/statuses/filter.json'
    query_data = [('language', 'en'), ('locations', '-130,-20,100,50'),('track','#')]
    #query_data = [('locations', '-130,-20,100,50'), ('track', '#')]
    query_url = url + '?' + '&'.join([str(t[0]) + '=' + str(t[1]) for t in query_data])
    response = requests.get(query_url, auth=my_auth, stream=True)
    print(query_url, response)
    return response


afinn = Afinn()
TCP_IP = "edge.example.com"
TCP_PORT = 9008
conn = None
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)
print("Waiting for TCP connection...")
conn, addr = s.accept()
print("Connected... Starting getting tweets.")
resp = get_tweets()
send_tweets_to_spark(resp,conn)



