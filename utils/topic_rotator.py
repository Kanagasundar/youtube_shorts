
import random
from datetime import datetime

# Define your 5 rotating niche categories and sample topics
topics_by_day = {
    0: ("Rare Historical Image", [
        "A 1911 photo of a floating house in Venice",
        "The last known photo of the Titanic before sinking",
        "When elephants were used in 1940s construction"
    ]),
    1: ("Banned or Forgotten Object", [
        "This cereal was banned for causing hallucinations",
        "Toys that were banned in the 90s",
        "A book cover so scary it got pulled from shelves"
    ]),
    2: ("AI Reimagines Alt History", [
        "What if Julius Caesar had a smartphone",
        "If Beethoven was a modern DJ",
        "Einstein as a video game character"
    ]),
    3: ("Hidden or Abandoned Places", [
        "A ghost town in California no one visits",
        "An underwater city off the coast of Japan",
        "A pyramid found in the middle of the jungle"
    ]),
    4: ("AI Recreates Childhood Toys", [
        "That 90s slime toy – recreated by AI",
        "What AI thinks Furbies looked like",
        "Remember HitClips? AI does"
    ])
}

def get_today_topic():
    day_index = datetime.now().weekday() % 5  # 0 = Monday ... 4 = Friday
    category, topic_list = topics_by_day[day_index]
    topic = random.choice(topic_list)
    return category, topic
