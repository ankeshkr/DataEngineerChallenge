# -*- coding: utf-8 -*-
"""Untitled3.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/17g89rapfJy-gAgrzkOqAZfCxZGQQGpoP
"""

# Pre requisite for working with google colab 
!apt-get update
!apt-get install openjdk-8-jdk-headless -qq > /dev/null
!wget -q http://archive.apache.org/dist/spark/spark-2.3.1/spark-2.3.1-bin-hadoop2.7.tgz
!tar xf spark-2.3.1-bin-hadoop2.7.tgz
!pip install -q findspark

import os
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-8-openjdk-amd64"
os.environ["SPARK_HOME"] = "/content/spark-2.3.1-bin-hadoop2.7"

!ls

import findspark
findspark.init()

# Import the libraries
from pyspark.sql import SparkSession
from pyspark.sql import Row
from pyspark.sql.types import *
from pyspark.sql.functions import *

# Spark Session
spark = SparkSession.builder.master("local").appName("Data Engineering Challenge").getOrCreate()
sc = spark.sparkContext

# the log file has been renamed to weblog.txt and uploaded in the google colab session
# Load the data by creating rdd
rdd = sc.textFile('weblog.txt')
# split the data from log text file on whitespaces into different columns
rdd = rdd.map(lambda line: line.split(" "))

# Taking the values from 1st, 3rd and 12th columns and RDD is converted to Dataframe
df_final = rdd.map(lambda line: Row(timestamp=line[0], ipaddress=line[2].split(':')[0],url=line[12])).toDF()
df_final.show(5)

# timestamp string field is converted to TimestampType for basic arithmetic
df_final = df_final.withColumn('timestamp', df_final['timestamp'].cast(TimestampType()))
df_final.show(5)

# Q1: SESSIONIZE THE WEB LOG BY IP.
# sessionize data based on 15 min fixed window time 
#assign an sequentially increasing Id as SessionId to each session
SessionDF = df_final.select(window("timestamp", "15 minutes").alias('FixedTimeWindow'),'timestamp',"ipaddress").groupBy('FixedTimeWindow','ipaddress').count().withColumnRenamed('count', 'NumberHitsInSessionForIp')
#SessionDF.show(2)
SessionDF = SessionDF.withColumn("SessionId", monotonically_increasing_id())
SessionDF.show(5,False)

# join the time stamps and url to the Sessionized DF
dfWithTimeStamps = df_final.select(window("timestamp", "15 minutes").alias('FixedTimeWindow'),'timestamp',"ipaddress","url")
SessionDF = dfWithTimeStamps.join(SessionDF,['FixedTimeWindow','ipaddress'])
SessionDF.show(2)

# Finding the first hit time of each ip for each session and join in to our session df
FirstHitTimeStamps = SessionDF.groupBy("SessionId").agg(min("timestamp").alias('FirstHitTime'))
SessionDF = FirstHitTimeStamps.join(SessionDF,['SessionId'])
SessionDF.select(col("SessionId"),col("ipaddress"),col("FirstHitTime")).show(20)

# TIME DURATION OF SESSION
# Duration of a session = time difference of first and last hit in a session 
# if there is only one hit in a session the duration is zero
timeDiff = (unix_timestamp(SessionDF.timestamp)-unix_timestamp(SessionDF.FirstHitTime))
SessionDF = SessionDF.withColumn("timeDiffwithFirstHit", timeDiff)
tmpdf = SessionDF.groupBy("SessionId").agg(max("timeDiffwithFirstHit").alias("SessionDuration"))
SessionDF = SessionDF.join(tmpdf,['SessionId'])
SessionDF.select(col("SessionId"),col("ipaddress"),col("SessionDuration")).show(20)

#Q2: AVEARAGE SESSION TIME
meandf = SessionDF.groupBy().avg('SessionDuration')
meandf.show(3)

#Q3: UNIQUE URL VISITS PER SESSION
# Determine unique URL visits per session. To clarify, count a hit to a unique URL only once per session
dfURL = SessionDF.groupBy("SessionId","URL").count().distinct().withColumnRenamed('count', 'hitURLcount')
dfURL.show(20)

#Q4: MOST ENGAGED USER
#find the IPs with the longest session times
EngagedUsers = SessionDF.select("ipaddress","SessionID","SessionDuration").sort(col("SessionDuration").desc()).distinct()
EngagedUsers.show(3)