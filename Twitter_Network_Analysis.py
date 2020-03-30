"""
The code in this file represents a social network of a user. It outputs network size in terms of nodes, edges, average distance and diameter.
These values are written in the file final_output.txt as well as printed on screen.
Note: In worst case it takes 45 min to run. Please be patient!
Pycharm is used to run this file.
"""

import twitter
from functools import partial
from sys import maxsize as maxint
import sys
import time
from urllib.error import URLError
from http.client import BadStatusLine
import operator
import networkx
import matplotlib.pyplot as plt

# The keys and tokens to access the twitter API
CONSUMER_KEY = 'abc'
CONSUMER_SECRET = 'abc'
OAUTH_TOKEN = 'abc'
OAUTH_TOKEN_SECRET = 'abc'

# Using OAuth method for authentication
auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET, CONSUMER_KEY, CONSUMER_SECRET)

# Accessing the Twitter API
twitter_api = twitter.Twitter(auth=auth)


# Function from cookbook to make a Twitter request
def make_twitter_request(twitter_api_func, max_errors=10, *args, **kw):
    def handle_twitter_http_error(e, wait_period=2, sleep_when_rate_limited=True):

        # Checks if the wait period of request is greater than 1 hr otherwise print the message
        if wait_period > 3600:  # Seconds
            print('Too many retries. Quitting.', file=sys.stderr)
            raise e

        # Following are the different errors that could be encountered during program execution and their corresponding error message
        if e.e.code == 401:
            print('Encountered 401 Error (Not Authorized)', file=sys.stderr)
            return None
        elif e.e.code == 404:
            print('Encountered 404 Error (Not Found)', file=sys.stderr)
            return None
        elif e.e.code == 429:
            print('Encountered 429 Error (Rate Limit Exceeded)', file=sys.stderr)
            if sleep_when_rate_limited:
                print("Retrying in 15 minutes...ZzZ...", file=sys.stderr)
                sys.stderr.flush()
                time.sleep(60 * 15 + 5)
                print('...ZzZ...Awake now and trying again.', file=sys.stderr)
                return 2
            else:
                raise e
        elif e.e.code in (500, 502, 503, 504):
            print('Encountered {0} Error. Retrying in {1} seconds'.format(e.e.code, wait_period), file=sys.stderr)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        else:
            raise e

    wait_period = 2
    error_count = 0

    # try and catch which will catch exception such as URLError, BadStatusLine or HTTP error
    while True:
        try:
            return twitter_api_func(*args, **kw)
        except twitter.api.TwitterHTTPError as e:
            error_count = 0
            wait_period = handle_twitter_http_error(e, wait_period)
            if wait_period is None:
                return
        except URLError as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("URLError encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise
        except BadStatusLine as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("BadStatusLine encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise


# Function from cookbook to fetch friends and followers for particular id
def get_friends_followers_ids(twitter_api, screen_name=None, user_id=None,
                              friends_limit=maxint, followers_limit=maxint):
    assert (screen_name != None) != (user_id != None), "Must have screen_name or user_id, but not both"

    get_friends_ids = partial(make_twitter_request, twitter_api.friends.ids,
                              count=5000)

    get_followers_ids = partial(make_twitter_request, twitter_api.followers.ids,
                                count=5000)

    friends_ids, followers_ids = [], []

    for twitter_api_func, limit, ids, label in [
        [get_friends_ids, friends_limit, friends_ids, "friends"],
        [get_followers_ids, followers_limit, followers_ids, "followers"]
    ]:

        if limit == 0: continue

        cursor = -1
        while cursor != 0:

            if screen_name:
                response = twitter_api_func(screen_name=screen_name, cursor=cursor)
            else:
                response = twitter_api_func(user_id=user_id, cursor=cursor)

            if response is not None:
                ids += response['ids']
                cursor = response['next_cursor']

            print('Fetched {0} total {1} ids for {2}'.format(len(ids), label, (user_id or screen_name)),
                  file=sys.stderr)

            if len(ids) >= limit or response is None:
                break

    return friends_ids[:friends_limit], followers_ids[:followers_limit]


# Fetching followers and friends of user screen name = 'sundarpichai'
friends_ids, followers_ids = get_friends_followers_ids(twitter_api,
                                                       screen_name="sundarpichai",
                                                       friends_limit=500,
                                                       followers_limit=500)

# Display the result of get_friends_followers_ids by showing list of friends and followers
print(friends_ids)
print(followers_ids)

# get reciprocal by using the set intersection and storing it in reciprocal list
reciprocal = list(set(friends_ids) & set(followers_ids))
print("\n Reciprocal List :", reciprocal)


# Function from cookbook to fetch the user profile data of a user to get number of followers
def get_user_profile(twitter_api, screen_names=None, user_ids=None):
    assert (screen_names != None) != (user_ids != None), "Must have screen_names or user_ids, but not both"

    items_to_info = {}

    items = screen_names or user_ids

    while len(items) > 0:

        items_str = ','.join([str(item) for item in items[:100]])
        items = items[100:]

        if screen_names:
            response = make_twitter_request(twitter_api.users.lookup,
                                            screen_name=items_str)
        else:
            response = make_twitter_request(twitter_api.users.lookup,
                                            user_id=items_str)

        for user_info in response:
            if screen_names:
                items_to_info[user_info['screen_name']] = user_info
            else:
                items_to_info[user_info['id']] = user_info

    return items_to_info


# Fetches the distance-1, distance-2 friends and so on till depth 2 by passing screen_name
def crawl_followers_by_screen_name(twitter_api, screen_name=None):
    # Fetching reciprocal and fetching its profile
    friends_ids, followers_ids = get_friends_followers_ids(twitter_api, screen_name, friends_limit=5000,
                                                           followers_limit=5000)
    reciprocal = set(friends_ids) & set(followers_ids)
    response = get_user_profile(twitter_api, user_ids=list(reciprocal))
    followers_dict = {}
    for user, val in response.items():
        followers_dict[user] = val['followers_count']

    # Sorting the dictionary to get top 5 followers
    followers_dict = dict(reversed(sorted(followers_dict.items(), key=operator.itemgetter(1))))
    return followers_dict


# Fetches the distance-1, distance-2 friends and so on till depth 2 by passing screen_id
def crawl_followers_by_id(twitter_api, id=None):
    # Fetching reciprocal and fetching its profile
    friends_ids, followers_ids = get_friends_followers_ids(twitter_api, user_id=id, friends_limit=5000,
                                                           followers_limit=5000)
    reciprocal_friends = set(friends_ids) & set(followers_ids)
    response = get_user_profile(twitter_api, user_ids=list(reciprocal_friends))
    count_dict = {}
    for user, val in response.items():
        count_dict[user] = val['followers_count']

    # Sorting the dictionary to get top 5 followers
    count_dict = dict(reversed(sorted(count_dict.items(), key=operator.itemgetter(1))))
    return count_dict


screen_name = "sundarpichai"

# dictionary to store result of crawl_followers_by_screen_name
resultDict = {}

# Fetching crawl_followers_screen_name result in result dictionary
resultDict.update(crawl_followers_by_screen_name(twitter_api, screen_name))

# getting top 5 with maximum number of followers
while len(resultDict) > 5:
    resultDict.popitem()

# Plotting the graph for starting node + other top 5 nodes
G = networkx.Graph()
G.add_node(screen_name)
for i in list(resultDict):
    G.add_node(i)
    G.add_edge(screen_name, i)

# Getting the user_ids from the dictionary
ids = resultDict.keys()
ids_list = list(ids)

print("ids_list\n", ids_list)
# store the result of crawling
crawlResults = {}

# Fetching next 100 nodes
for x in range(30):
    i = ids_list[x]
    crawlResults = crawl_followers_by_id(twitter_api, i)

    while len(crawlResults) > 5:
        crawlResults.popitem()

    # Plotting the graph for the next nodes
    for k in list(crawlResults):
        G.add_node(k)
        G.add_edge(i, k)

    # getting more nodes
    for k in (list(crawlResults.keys())):
        ids_list.append(k)

# prints total number of the next nodes
print(ids_list)

# Display the graph
networkx.draw(G, with_labels=False)
plt.draw()
plt.show()

# Write final output to a file
f = open("final_output.txt", "w")
f.write("A social network is created\n")
f.write("Number of nodes is: " + str(networkx.number_of_nodes(G)))
f.write("\nNumber of edges is: " + str(networkx.number_of_edges(G)))
f.write("\nAverage Distance is: " + str(networkx.average_shortest_path_length(G)))
f.write("\nAverage Diameter is: " + str(networkx.diameter(G)))

# Write final output to a screen
print("A social network is created\n")
print("Number of nodes is: " + str(networkx.number_of_nodes(G)))
print("\nNumber of edges is: " + str(networkx.number_of_edges(G)))
print("\nAverage Distance is: " + str(networkx.average_shortest_path_length(G)))
print("\nAverage Diameter is: " + str(networkx.diameter(G)))
