#!/usr/bin/python3
'''Playing with python elasticsearch low level client'''
import requests, json, urllib.parse
import sys
from pprint import pprint
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, DocType

# connect to ES server
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

index = 'event_test'
doc_type = 'event_info'

def check_setup():
    '''check ES is up and running'''
    res = requests.get('http://localhost:9200')
    print(res.content)

def delete_index(index):
    '''delete index if it exists'''
    if es.indices.exist(index=index):
        es.indices.delete(index=index)

def create_index(index):
    '''create empty index with customized setting & mapping'''
    # customize analyzer for english stemming, possessives, and synonyms
    english_synonym = {
        "analysis": {
            "filter": {
                "english_stop": {
                    "type": "stop",
                    "stopwords":  "_english_"
                },
                "english_stemmer": {
                    "type": "stemmer",
                    "language": "english"
                },
                "english_possessive_stemmer": {
                    "type": "stemmer",
                    "language": "possessive_english"
                },
                "synonym": {  # set synonym filter with synonyms from WordNet
                    "type": "synonym",
                    "format": "wordnet",
                    "synonyms_path": "analysis/wn_s.pl"
                }
            },
            "analyzer": {
                "english_synonym": {
                    "tokenizer":  "standard",
                    "filter": [
                        "synonym",
                        "english_possessive_stemmer",
                        "lowercase",
                        "english_stop",
                        "english_stemmer"
                    ]
                }
            }
        }
    }

    # defineA mapping to allow geo point data type
    mapping = {
        "properties" : {
            "address" : {"type" : "keyword"},
            "location": {"type": "geo_point"},
            "cost" : {"type" : "long"},
            "date" : {"type" : "keyword"}, # REVISIT with date datatype
            "link" : {"type" : "keyword"},
            "name" : {"type" : "text", "analyzer": "english_synonym"},
            "tags" : {"type" : "text", "analyzer": "english_synonym"},
            "time" : {"type" : "keyword"}, # REVISIT
            "image_url": {"type": "keyword"},
            "description": {"type" : "text", "analyzer": "english_synonym"},
            "venue": {"type": "keyword"}
        }
    }

    setting = {
        "settings": english_synonym,
        "mappings": {"event_info": mapping}
    }

    # create index if it doesn't already exist
    if not es.indices.exists(index=index):
        es.indices.create(index=index, body=setting)

def store_docs(index, doc_type, events):
    '''store event data in elasticsearch.

    Args:
        events(list): a list of event data in dictionary form
            e.g. [event1, event2...] where each event is a dict

    Note: document id starts with 0
    '''
    i = 0
    while i < len(events):
        event = "event" + str(i + 1)
        es.index(index=index, doc_type=doc_type, id=i, body=events[i][event])
        i += 1


def get_num_docs(index, doc_type):
    '''return the number of docs saved in an index'''
    if es.indices.exist(index=index):
        num_docs = es.count(index=index, doc_type=doc_type)['count']
        print("number of documents: ", num_docs)

    return num_docs


def addr_to_geo(index, doc_type, doc_id):
    '''
    Look up latitude & longitude based on address for the doc id specified.

    Returns:
        A dict of location in lat & lon.
        e.g. {'doc': {'location': {'lat': lat, 'lon': lng}}}
    '''
    api_key = 'AIzaSyAgPeDFl_wsFFzBfmtG0HY77Z_UXYYsiOE'

    addr = es.get(index=index, doc_type=doc_type, id=i)['_source']['address']
    print(addr)
    addr_lookup = {'address': addr, 'key': api_key}
    addr_url = urllib.parse.urlencode(addr_lookup)
    geo = requests.get('https://maps.googleapis.com/maps/api/geocode/json?{}'.format(addr_url))

    if geo.status_code == 200:
        lat = geo.json()['results'][0]['geometry']['location']['lat']
        lng = geo.json()['results'][0]['geometry']['location']['lng']
        geo_location = {'doc': {'location': {'lat': lat, 'lon': lng}}}
        print(geo_location)
        return geo_location
    else:
        print("geo request failed")
        sys.exit()


def save_geo(index, doc_type, doc_id, geo_location):
    '''save the geo-coordinates to ES for the doc id specified'''
    es.update(index=index, doc_type=doc_type, id=doc_id, body=geo_location)


if __name__ == '__main__':
    # delete existing index and create a new one to laod new data
    delete_index(index=index)
    create_index(index=index)

    # store new data
    store_docs(index=index, doc_type=doc_type, events)

    # save data location in geo-coordinates
    num_docs = get_num_docs(index=index, doc_type=doc_type)
    i = 0
    while i < num_docs:
        geo = addr_to_geo(index=index, doc_type, i)
        save_geo(index=index, doc_type=doc_type, i, geo)
        i += 1
'''
# update mapping after index creation
es.indices.put_mapping(index='event_test', doc_type='event_info', body=setting['mappings']['event_info'])
'''

event1 = {
    "address" : "533 Sutter Street, San Francisco, CA",
    "time" : "10pm",
    "description" : "Laugh out loud every Friday and Saturday night with Secret Improv Society: San Francisco's award-winning, interactive, late-night comedy show! Each unique show features fast-paced scenes and songs inspired by audiences and made up on the spot.\n\nPerformances are held in a cozy underground theater, conveniently located near Union Square, with a full bar, no drink minimums, and free Oreos. Itâs a perfect date night, group night, and a must-see attraction for locals and visitors alike. Shows can sell-out, so rather than take your chances at the door, get discounted tickets at https://www.secretimprov.com.\n\nNEW: To celebrate their phenomenal ten year run, Secret Improv is adding 8pm shows to their current 10pm Fri./Sat. line-up beginning June 1, 2018. The 8pm show will be the same fast-paced and interactive format as the original 10pm \"late-night\" show...only earlier. Tickets at https://www.secretimprov.com.\n",
    "venue" : "Shelton Theater",
    "image_url" : "https://cdn.sfstation.com/assets/images/events/0231/2312744/1490403003-2312744a_orig.jpg",
    "date" : "Fri May 18",
    "link" : "https://www.sfstation.com//secret-improv-society-late-night-comedy-e2312744",
    "cost" : 19,
    "tags" : [
            "Comedy",
            "Dating",
            "Drinks",
            "Theater / Performance Arts"
    ],
    "name" : "Secret Improv Society Late-Night Comedy",
    'location': {
        'lat': 0.0,
        'lon': 0.0
    }
}

event2 = {
    "address" : "1192 Folsom Street, San Francisco, CA",
    "time" : "10pm-2am",
    "description" : "UHAUL SF!\nWe’re San Francisco’s Party For Girls Who Love Girls! ?\nCreating safe space for women since 2014.\n? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ?\n\nGet the “URGE TO MERGE” on the dance floor with…\n\n?opening set by?\n\n? KOSLOV (San Francisco)\nKoslov is a East Bay Native going on 8 years on vinyl. This babe has opened for artists such as Syd The Kyd, DJ Theory and headlined events in NYC for pride afterparties. Koslov’s vibe is a mixture of dancehall, hiphop, dembow, soul, reggaeton and funk. Catch this part time DJ and full time 2nd grade teacher on decks from 10pm – 12am ????\n@skoslovich\nhttps://www.soundcloud.com/skoslov\n? ? ?\n\n? CHINA G (San Francisco)\nChina G is definitely a G. An OG. Mixin’ up tracks since the good ol’ Rebel Girl, Cockblock, Hotpants days. Know about those? Then you’re a muthaf*kken O.G. as well. You can skip a gym day coz’ CHINA G is gonna make you WERRRK that dance floor ????\n*Throws a backwards peace sign*\n? ? ?\n@djchinag\nhttps://www.soundcloud.com/djchinag\n\n? ? Bossy SF Entertainment GOGO GALS ? ?\n\n? ? show your ID with proof of U-hauling with your wifey & get in FREE before 10:30pm ? ? (Matching address on both ID’s)\n\n3rd Friday @ F8\n1192 Folsom Street SF\n21+\n\n$5 w/ RSVP entry before 10:30pm will be donated to The San Francisco Dyke March ?\n$15 after.\n\n? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ?\n",
    "venue" : "F8 | 1192 Folsom",
    "image_url" : "https://cdn.sfstation.com/assets/images/events/0235/2350376/1526445905-2350376a_orig.jpg",
    "date" : "Fri May 18",
    "link" : "https://www.sfstation.com//uhaul-sf-ft-koslov-china-g-e2350376",
    "tags" : [
        "Drinks",
        "Clubs",
        "Music"
    ],
    "cost": -1,
    "name" : "UHAUL SF ft. Koslov + China G",
    'location': {
        'lat': 0.0,
        'lon': 0.0
    }
}

event3 = {
    "address" : "200 Larkin St, San Francisco, CA",
    "time" : "9pm",
    "description" : "The Center for Asian American Media presents CAAMFest36, a 15-day celebration of film, music and food. This year, we moved our fest to run right in the heart of Asian Pacific Heritage month, May 10 through the 24th. Featuring a diverse showcase of over 100 narratives, documentaries, concerts and special events, CAAMFest comes to life in over 20 venues across San Francisco and Oakland. \n\n\n\nHighlights from this year's program include:\n\n\nGala Presentations:\n\nAn American Hero: Norman Mineta and his Legacy (Opening Night)\nBitter Melon\nOrigin Story\nAunt Lily’s Flower Book (Closing Night)\n\n\nSpecial Presentations\n\nMeditation Park \nCome Drink with Me \nGolden Swallow\n\n\nMusic and Live Performances\n\nHeritage SF\nDirections in Sound - https://caamfest.com/2018/events/directions-in-sound/\nAnatomy of a Music Video with Warren Fu - https://caamfest.com/2018/events/anatomy-of-a-music-video-w-warren-fu/\nAnatomy of a Music Video with Ruby Ibarra\n\n\nFood\n\nFirst Kitchen\nJimami Tofu\nLumpia (15th Anniversary)\nUlam: Main Dish\n\n\nNarrative:\n\n20 Weeks\nDead Pigs\nEat a Bowl of Tea (Out of the Vaults)\nGo for Broke: An Origin Story\nHalf Window\nI Can, I Will, I Did\nSaving Sally\nStand Up Man\nUnlovable\nWhite Rabbit\n\n\nDocumentaries:\n\nA Little Wisdom\nA Time to Swim\nHavana Divas\nLate Life: The Chien-Ming Wang Story\nLooking For?\nMinding the Gap\nNailed It\nThe People’s Republic of Desire\nThe Registry\n\n\nShorts Programs:\n\nAltered States\nEpisodics\nFighters & Dreamers\nIn Transition\nLife, Animated\nMade you a Mixtape\nOut/Here\nWomen on the Rise\n\n\nCheck out the full program, watch trailers, and get tickets at https://caamfest.com/2018/schedule/ .\n\n\n--------\n\nCAAMFest is the nation's largest showcase for new Asian American and Asian films in San Francisco, Berkeley and Oakland. Since 1982, the festival has been an important launching point for Asian American independent filmmakers as well as a vital source for new Asian cinema.\n\nhttps://www.facebook.com/CAAMFest/\nhttps://twitter.com/caam\n",
    "venue" : "Starline Social Club",
    "image_url" : "https://cdn.sfstation.com/assets/images/events/0185/1853652/1454632881-1853652a_orig.jpg",
    "date" : "Fri May 18",
    "link" : "https://www.sfstation.com//caamfest-2018-e1853652",
    "tags" : [
        "Film / Television",
        "Music",
        "Festival / Fair"
    ],
    "name" : "CAAMFest 2018",
    "cost": -1,
    'location': {
        'lat': 0.0,
        'lon': 0.0
    }
}

event4 = {
    "address" : "474 Valencia Street, San Francisco, CA",
    "time" : "7pm doors, 8pm performances, 10pm comedy",
    "description" : "#ETC\n\nA weekly showcase (with food) consisting of artists, poets, musicians, and comedians. Donation based, all-ages, plus an authentic Bay Area cultural experience!\n\nHost: Larry Dorsey Jr. (comedian, writer, radio personality)\n",
    "venue" : "Black and Brown Social Club",
    "image_url" : "https://cdn.sfstation.com/assets/images/events/0234/2347535/1524177433-2347535a_orig.jpg",
    "date" : "Fri May 18",
    "link" : "https://www.sfstation.com//equiptos-timeless-cypher-e2347535",
    "cost" : 0,
    "tags" : [
        "Comedy",
        "Art",
        "Community",
        "Music",
        "Theater / Performance Arts"
    ],
    "name" : "Equipto's Timeless Cypher",
    'location': {
        'lat': 0.0,
        'lon': 0.0
    }
}

event5 = {
    "address" : "2781 24th Street, San Francisco, CA",
    "time" : "8pm",
    "description" : "Topsy-Turvy Queer Circus presents\n\nPARADISE: Belly of the Beast\n\nTopsy-Turvy Queer Circus presents the final installment of its Afrosurrealist trilogy PARADISE: Belly of the Beast. As doubt and disorder overtake her world, the fallen Angel must face her fears to unify the gods of PARADISE and defy the beast that stalks them. Told through a blend of aerial and acrobatic dance alongside vogue, hip hop and film, this epic finale features a stellar cast of queer and trans performing artists of color.\n\nPARADISE is co-produced by India Sky Davis and Indi McCasey, directed by Davis and Gabriel Christian and features Davis and former Cirque du Soleil performer Marshall Jarreau, alongside artists including Kiebpoli Calnek, Brandon Kazen-Maddox, Davia Spain, The Lady Ms. Vagina Jenkins, and Saturn Rising.'\n\nCelebrating its 6th year as part of the National Queer Arts Festival, Topsy-Turvy Queer Circus organizes multidisciplinary circus arts productions that challenge and subvert traditional ideals of beauty, gender, sexuality and power. For more info please visit topsyturvycircus.org.\n\nThis event is sponsored by Brava Theater and Queer Cultural Center with generous support from the San Francisco Arts Commission, California Arts Council, Horizons Foundation, Grants for the Arts, the Zellerbach Family Foundation, and the National Arts and Disability Center at the University of California Los Angeles.\n",
    "venue" : "Brava Theater Center",
    "image_url" : "https://cdn.sfstation.com/assets/images/events/0235/2350804/1526687883-2350804a_orig.jpg",
    "date" : "Fri May 18",
    "link" : "https://www.sfstation.com//paradise-belly-of-the-beast-e2350804",
    "cost": -1,
    "tags" : [
        "Theater / Performance Arts"
    ],
    "name" : "PARADISE: Belly of the Beast",
    'location': {
        'lat': 0.0,
        'lon': 0.0
    }
}

event6 = {
    "name" : "The Color Purple - A Broadway Musical",
    "tags" : [
        "Dance (performance)",
        "Music",
        "Theater / Performance Arts"
    ],
    "time" : "8PM",
    "address" : "1192 Market St., San Francisco, CA",
    "description" : "Prepare for one of the most thought-provoking, moving, emotional and ultimately uplifting musicals of the season – John Doyle’s startling, stripped-back adaption of The Color Purple. Enthusiastically received by audiences and critics, this Broadway revival has thrice the weight of the original – and that’s saying something. Empowering and culturally significant, The Color Purple gives new meaning to musical theatre as a performance medium.\n\nThe Color Purple Tickets\nOrpheum Theatre Tickets\nThings To Do In San Francisco\n",
    "image_url" : "https://cdn.sfstation.com/assets/images/events/0234/2349132/1525469327-2349132a_orig.jpg",
    "venue" : "SHN Orpheum Theatre",
    'location': {
        'lat': 0.0,
        'lon': 0.0
    },
    "link" : "https://www.sfstation.com//the-color-purple-a-broadway-musical-e2349132",
    "date" : "Fri May 18",
    "cost": -1
}

event7 = {
    "link" : "https://www.sfstation.com//cheaper-than-therapy-e2062971",
    "date" : "Fri May 18",
    "name" : "Cheaper Than Therapy",
    "tags" : [
        "Comedy"
    ],
    "time" : "10pm",
    "address" : "406 Clement Street, San Francisco, CA",
    "description" : "Come spend an intimate evening enjoying unadulterated stand-up comedy with some of the best comedians from the Bay Area and beyond at Cheaper Than Therapy. The show is every Thursday, Friday, and Saturday at 10pm and every Sunday at 7pm. You'll get a healthy dose of laughs at San Francisco's historic Shelton Theater. Come learn that laughter really is the best medicine.\n\nProduced by the formidable comedic trio of Eloisa Bravo, Scott Simpson, and Jon Allen, the show offers you an evening of great stand-up comedy, as well as access to a wide variety of reasonably priced alcoholic beverages. \n\nCheck in with the box office downstairs when you arrive. The bar opens at 9pm and the show starts at 10pm, so come early for cheap drinks and great seats. While everyone is welcome at the theater, the show is really only appropriate for mature audiences, so 18 and up is strongly advised due to the adult nature of the material. Hey, it is stand-up comedy after all.\n\nAfter the show, everyone over 21 is encouraged to come to an after party at the neighborhood bar.\n\nWebsite: http://cttcomedy.com\nTickets: https://cttcomedy.eventbrite.com\nYelp: https://bit.ly/cttyelp\nFacebook: https://fb.me/cttcomedy\nInstagram: https://instagram.com/cttcomedy\n\nEloisa Bravo has performed at the Punch Line, the Purple Onion, Cobb's and Rooster T. Feathers, as well as Palm Beach, Miami, and Hollywood improv shows. She has won several comedy competitions in the San Francisco Bay Area and performed at many festivals and showcases. \n\nJon Allen has performed at the Punch Line in San Francisco, Cap City Comedy Club in Austin, Texas, and regularly performs in venues throughout the New York City area. Allen's work has appeared in Wired Magazine, Tech Crunch, Savage Henry, and The Rachel Maddow Blog, in addition to his numerous physics publications. You can find him on Twitter at https://twitter.com/mathturbator.\n\nScott Simpson has performed at SF Sketchfest, the Punch Line in San Francisco, the Bridgetown Comedy Festival, and the North American Comedy and Music Festival. Simpson's show \"You Look Nice Today\" has received the Podcast Award for Best Comedy Podcast and his jokes can be found on the illustrious twitter at https://twitter.com/scottsimpson.\n\nEach week, Jon, Eloisa, and Scott are joined by the three of the best comics from the Bay Area and beyond to bring you a fresh, exciting ~75 minutes of stand-up comedy. The bar opens at 9pm on Thursday through Saturday and 6pm on Sundays, so come out early and have a few drinks before the show starts.\n",
    "image_url" : "https://cdn.sfstation.com/assets/images/events/0206/2062971/1490895613-2062971a_orig.png",
    "venue" : "Shelton Theater",
    "cost": -1,
    'location': {
        'lat': 0.0,
        'lon': 0.0
    }
}

event8 = {
    "link" : "https://www.sfstation.com//ben-nicky-e2347410",
    "cost" : 20,
    "date" : "Fri May 18",
    "name" : "Ben Nicky",
    "tags" : [
        "Clubs",
        "Music"
    ],
    "time" : "10:00 PM to 3:00 AM",
    "address" : "540 Howard Street, San Francisco, CA",
    "description" : "Temple Nightclub Presents Ben Nicky\n\nBen Nicky is a British trance DJ who has played at some of the world's biggest electronic music festivals, including Nature One, Tomorrowland and A State of Trance. He has racked up millions of plays across a variety of online platforms with tracks like \"Drop,\" \"The One\" and \"Hectic.\"\n\nContact us at 415.312.3668 or [email protected] for reservations.\n\nThis is a 21+ event.\n",
    "image_url" : "https://cdn.sfstation.com/assets/images/events/0234/2347410/1526341037-2347410a_orig.jpg",
    "venue" : "Temple SF",
    'location': {
        'lat': 0.0,
        'lon': 0.0
    }
}



'''
# query data with specific tags
# terms search through inverted index, which converts tokens into lowercase
print("All events with the tag 'Family' and/or 'Arts':")
pprint(es.search(index='event_test', doc_type='event_info',
                 body={"query": {
                     'constant_score': {
                         'filter': {
                             'terms': {  # search multiple terms (or)
                                 'tags': ['family', 'arts']
                             }
                         }
                     }
                 }
                   }))


# query data with cost range
print("All events with price range between 0 and 30:")
pprint(es.search(index='event_test', doc_type='event_info',
                 body={"query": {
                     'constant_score': {
                         'filter': {
                             'range': {
                                 'cost': {
                                     'gte': 0,
                                     'lt': 30
                                 }
                             }
                         }
                     }
                 }
                   }))
'''
'''
# combined queries
geo_only_query = {
    'geo_distance': {
        'distance': "6mi",
        'location': {
            'lat': 37.773972,
            'lon': -122.431297
        }
    }
}


# This works!
geo_full_query = {
    'query': geo_only_query
}

cost_only_query = {
    'range': {
        'cost': {
            'gte': 0, 'lte': 1000
            }
    }
}

# This works
cost_full_query = {
    'query': {
        'constant_score': {
            'filter': cost_only_query
        }
    }
}

event_tag_query = {
    'terms': {
        'tags': ["art", "club"]
    }
}

all_events_query = {
    'query': {
        'constant_score': {
            'filter': {
                'bool': {
                    'must': [
                        cost_only_query,
                        geo_only_query
                    ]
                }
            }
        }
    }
}

# This works
no_keywords_query = {   # need to implement date & time range
    'query': {
        'bool': {
            'must': {
                'multi_match': {
                    'query': "art/club",
                    'fields': "tags",
                    'fuzziness': 'AUTO'
                }
            },
            'should': {
                'multi_match': {
                    'query': "art/club",
                    'fields': 'name',
                    'fuzziness': 'AUTO'
                }
            },
            'filter': {
                'bool': {
                    'must': [
                        cost_only_query,
                        geo_only_query
                    ]
                }
            }
        }
    }
}

# This works
keywords_query = {   # need to implement date & time range
    'query': {
        'multi_match': {  # REVISIT: add boost to specific fields
            'query': "Friday light",
            'type': 'best_fields',  # the default
            'fields': ['name', 'tags'],
            'fuzziness': 'AUTO'  # in case of user typo
            # REVISIT: Set Analyzer for intelligently finding synonyms
        }
    }
}

# this works!
keywords_query_plus_filter = {   # need to implement date & time range
    'query': {
        'bool': {
            'must': {
                'multi_match': {  # REVISIT: add boost to specific fields
                    'query': "Friday music",
                    'type': 'best_fields',  # the default
                    'fields': ['name', 'tags'],
                    'fuzziness': 'AUTO'  # in case of user typo
                    # REVISIT: set minimum_should_match %
                    # to display more relevant results
                    # REVISIT: Set Analyzer for intelligently finding synonyms
                }
            },
            'filter': {
                'bool': {
                    'must': [
                        cost_only_query,
                        geo_only_query
                    ]
                }
            }
        }
    }
}
'''
'''
print("All events containing the keywords:")
del no_keywords_query['query']['bool']['must']
del no_keywords_query['query']['bool']['should']

pprint(no_keywords_query)

pprint(es.search(index='event_test', doc_type='event_info', body=keywords_query))
'''
'''
# Getting specific field attribute values
pprint(es.get(index='event_test', doc_type='event_info', id=1))
pprint(es.count(index='event_test', doc_type='event_info')['count'])
pprint(es.get(index='event_test', doc_type='event_info', id=1)['_source']['address'])
'''
