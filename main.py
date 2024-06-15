#  Copyright (c) 2024 Prasham Shah. All rights reserved.

import instaloader
import nltk
import nltk.corpus
import nltk.sentiment
import nltk.tokenize

analyzer = nltk.sentiment.vader.SentimentIntensityAnalyzer()


def preprocess(text: str) -> str:
    """
    Preprocess text
    :param text: text to be preprocessed
    :type text: str
    :return: processed text
    :rtype: str
    """
    # Tokenization
    tokens = nltk.tokenize.word_tokenize(text.lower())

    # Stopwords
    stopwords = nltk.corpus.stopwords.words('english')
    tokens = [token for token in tokens if token not in stopwords]

    # Lemmatize
    lemmatizer = nltk.WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(token) for token in tokens]

    # Rejoin
    final = ' '.join(tokens)

    return final


def threat_analysis(text: str) -> float:
    """
    Rate the threat level of a text
    :param text: text to be evaluated
    :type text: str
    :return: threat level (lower is more threatening)
    :rtype: float
    """
    analyzer_text = preprocess(text)

    # Threat
    threat_score = 0

    # Threatening words
    threat = ['kill', 'die', 'death', 'hate', 'destroy', 'massacre',
              'slaughter']  # TODO: Add more and use a vector database

    for word in analyzer_text:
        if word in threat:
            threat_score -= 1

    # Sentiment
    sentiment = analyzer.polarity_scores(analyzer_text)
    threat_score += sentiment["compound"] * 5  # TODO: Consider using "neg" or another factor instead

    return threat_score


def instagram_threat_assessment(username: str) -> float:
    """
    Assess the threat level of an Instagram user
    :param username: Instagram handle
    :type username: str
    :return: threat level of the user
    :rtype: float
    """
    # Get user information
    bot = instaloader.Instaloader()
    profile = instaloader.Profile.from_username(bot.context, username)

    # Threat
    threat_score = 0

    # Information
    biography = profile.biography
    threat_score += threat_analysis(biography)

    # Posts
    posts = profile.get_posts()

    recency_factor = 1  # Decrease importance of older posts
    for post in posts:
        if post.caption is not None:
            threat_score += threat_analysis(post.caption) * recency_factor
        recency_factor /= 1.5

    return threat_score


def grades_threat_assessment(grades: list) -> float:
    """
    Determines the level/mental state of a student based on changes in grades
    :param grades: array of grades in the format [before, after], with each grade in the format {subject: grade},
    where the grade ranges from 0 to 1
    :type grades: list
    :return: threat level of the student
    :rtype: float
    """
    # Threat
    threat_score = 0

    for subject in grades[1]:
        threat_score += grades[1][subject] - grades[0][subject]

    return threat_score


def summative_threat_assessment(username: str, grades: list) -> float:
    """
    Summative threat assessment
    :param username: Instagram handle
    :type username: str
    :param grades: array of grades in the format [before, after], with each grade in the format {subject: grade},
    where the grade ranges from 0 to 1
    :type grades: list
    :return: threat level of the user
    :rtype: float
    """
    instagram_score = instagram_threat_assessment(username)
    grades_score = grades_threat_assessment(grades)

    return instagram_score + grades_score
