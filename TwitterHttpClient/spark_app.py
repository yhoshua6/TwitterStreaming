from pyspark import SparkConf,SparkContext
from pyspark.streaming import StreamingContext
from pyspark.sql import Row,SQLContext
import sys
import requests

# create spark configuration
conf = SparkConf()
conf.setAppName("TwitterStreamApp")
# create spark instance with the above configuration
sc = SparkContext(conf=conf)
sc.setLogLevel("ERROR")
# creat the Streaming Context from the above spark context with window size 2 seconds
ssc = StreamingContext(sc, 2)
# setting a checkpoint to allow RDD recovery
ssc.checkpoint("checkpoint_TwitterApp")
# read data from port 9009
dataStream = ssc.socketTextStream("edge.example.com",9007)


def aggregate_tags_count(new_values, total_sum):
    return sum(new_values) + (total_sum or 0)

def get_sql_context_instance(spark_context):
    if ('sqlContextSingletonInstance' not in globals()):
        globals()['sqlContextSingletonInstance'] = SQLContext(spark_context)
    return globals()['sqlContextSingletonInstance']


def send_df_to_dashboard(df):
    # extract the hashtags from dataframe and convert them into array
    top_tags = [str(t.hashtag) for t in df.select("hashtag").collect()]
    # extract the counts from dataframe and convert them into array
    tags_count = [p.hashtag_count for p in df.select("hashtag_count").collect()]
    # initialize and send the data through REST API
    #url = 'http://3.85.214.201:5001/updateData'
    url = 'http://edge.example.com:5001/updateData'
    request_data = {'label': str(top_tags), 'data': str(tags_count)}
    response = requests.post(url, data=request_data)

def send_sentiment_to_dashboard(df):
    # extract the hashtags from dataframe and convert them into array
    top_tags = ["Positive","Negative","Neutral"]
    # extract the counts from dataframe and convert them into array
    tags_count = [df.select("count").collect()[0][0],df.select("count").collect()[1][0],df.select("count").collect()[2][0]]
    print(tags_count)
    url = 'http://edge.example.com:5001/updateDataSentiment'
    request_data = {'label': str(top_tags), 'data': str(tags_count)}
    response = requests.post(url, data=request_data)


def process_rdd(time, rdd):
    print("----------- %s -----------" % str(time))
    try:
        # Get spark sql singleton context from the current context
        sql_context = get_sql_context_instance(rdd.context)
        # convert the RDD to Row RDD
        row_rdd = rdd.map(lambda w: Row(hashtag=w[0], hashtag_count=w[1]))
        # create a DF from the Row RDD
        hashtags_df = sql_context.createDataFrame(row_rdd)
        # Register the dataframe as table
        hashtags_df.registerTempTable("hashtags")
        # get the top 10 hashtags from the table using SQL and print them
        hashtag_counts_df = sql_context.sql("select hashtag, hashtag_count from hashtags order by hashtag_count desc limit 10")
        hashtag_counts_df.show()
        # call this method to prepare top 10 hashtags DF and send them
        send_df_to_dashboard(hashtag_counts_df)
    except:
        e = sys.exc_info()[0]
        print("Error: %s" % e)


def process_sentiment_rdd(time, rddp):
    print("+++++++++++++ %s +++++++++++++++" % str(time))
    try:
        # Get spark sql singleton context from the current context
        sql_context = get_sql_context_instance(rddp.context)
        # convert the RDD to Row RDD
        row_rdd = rddp.map(lambda w: Row(count = int(w)))
        # create a DF from the Row RDD
        hashtags_df = sql_context.createDataFrame(row_rdd)
        # Register the dataframe as table
        hashtags_df.registerTempTable("hashtags")
        # get the top 10 hashtags from the table using SQL and print them
        hashtag_counts_df = sql_context.sql("select * from hashtags")
        hashtag_counts_df.show()
        # call this method to prepare top 10 hashtags DF and send them
        send_sentiment_to_dashboard(hashtag_counts_df)
    except:
        e = sys.exc_info()[0]
        print("Error: %s" % e)

def isfloat(value):
    try:
       float(value)
       return True
    except ValueError:
       return False

def sentiment(avg_senti_val):
	try:
		if float(avg_senti_val) < 0: return 'NEGATIVE'
		elif float(avg_senti_val) == 0 or float(avg_senti_val) == 0.0: return 'NEUTRAL'
		else: return 'POSITIVE'
	except TypeError:
		return 'NEUTRAL'

# split each tweet into words

tweets = dataStream.flatMap(lambda text : text.split("\n"))
#tweets = tweets.filter(lambda line: '#' in line)

prevFloat = tweets.filter(lambda x : isfloat(x) == True)
total = prevFloat.count()
positive = prevFloat.filter(lambda x : sentiment(x) == 'POSITIVE').count()
negative = prevFloat.filter(lambda x : sentiment(x) == 'NEGATIVE').count()
neutral = prevFloat.filter(lambda x : sentiment(x) == 'NEUTRAL').count()

#all = total.union(positive)
all = positive.union(negative)
all = all.union(neutral)

#all = total.zip(positive).collect()
#all.pprint()

all.foreachRDD(process_sentiment_rdd)

words = dataStream.flatMap(lambda line: line.split(" "))
hashtags = words.filter(lambda w: '#' in w).map(lambda x: (x, 1))

# adding the count of each hashtag to its last count
tags_totals = hashtags.updateStateByKey(aggregate_tags_count)

# do processing for each RDD generated in each interval
tags_totals.foreachRDD(process_rdd)

# start the streaming computation
ssc.start()
# wait for the streaming to finish
ssc.awaitTermination()



