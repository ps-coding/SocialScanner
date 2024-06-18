#  Copyright (c) 2024 Prasham Shah. All rights reserved.
import dataclasses
import datetime
import itertools
import tkinter as tk

import instaloader
import nltk
import nltk.corpus
import nltk.sentiment
import nltk.tokenize

sentiment_analyzer = nltk.sentiment.vader.SentimentIntensityAnalyzer()
instagram_bot = instaloader.Instaloader()


def preprocess_text(text: str) -> str:
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


def text_health_analysis(text: str) -> float:
    analyzer_text = preprocess_text(text)

    health_score = 0

    # Concerning words
    concerning_words = ['kill', 'die', 'death', 'hate', 'destroy', 'massacre',
                        'slaughter', 'depression', 'depressed', 'sad', 'sadness', 'suicide', 'murder', 'hatred']

    for word in analyzer_text:
        if word in concerning_words:
            health_score -= 0.5

    # Sentiment analysis
    sentiment = sentiment_analyzer.polarity_scores(analyzer_text)
    health_score -= sentiment["neg"] * 5
    health_score += sentiment["compound"] * 2

    return health_score


@dataclasses.dataclass
class InstagramHealthAssessment:
    @dataclasses.dataclass
    class AssessmentResult:
        caption: str
        date: datetime.datetime
        health_score: float

    overall_health_score: float
    results: list[AssessmentResult]


def instagram_health_assessment(username: str) -> InstagramHealthAssessment:
    profile = instaloader.Profile.from_username(instagram_bot.context, username)

    health_score = 0
    results = []

    # Bio
    biography = profile.biography
    health_score += text_health_analysis(biography)
    results.append(InstagramHealthAssessment.AssessmentResult("(BIO) " + biography, datetime.datetime.now(),
                                                              health_score))

    # Posts
    posts = profile.get_posts()

    recency_factor = 1  # Decrease importance of older posts
    for post in itertools.islice(posts, 0, 20):
        if post.caption is not None:
            current_health_score = text_health_analysis(post.caption)
            results.append(
                InstagramHealthAssessment.AssessmentResult(post.caption, post.date_utc, current_health_score))
            health_score += current_health_score * recency_factor
        recency_factor /= 1.5

    if len(results) == 0:
        return InstagramHealthAssessment(0, [InstagramHealthAssessment.AssessmentResult("(ERROR) No information found.",
                                                                                        datetime.datetime.now(), 0)])

    return InstagramHealthAssessment(health_score / len(results), results)


@dataclasses.dataclass
class GradesHealthAssessment:
    @dataclasses.dataclass
    class AssessmentResult:
        subject: str
        change: float

    overall_health_score: float
    results: list[AssessmentResult]


def grades_health_assessment(grades: list) -> GradesHealthAssessment:
    health_score = 0
    results = []

    for subject in grades[1]:
        if subject in grades[0]:
            difference = grades[1][subject] - grades[0][subject]
            results.append(GradesHealthAssessment.AssessmentResult(subject, difference))
            health_score += difference

    if len(results) == 0:
        return GradesHealthAssessment(0, results)

    return GradesHealthAssessment(health_score / len(results), results)


previous_grades = {}
current_grades = {}


def add_previous_grade():
    global previous_grades
    subject, grade = previous_grades_entry.get().split(":")
    subject = subject.strip().lower()
    grade = grade.strip()
    previous_grades[subject] = float(grade) / 100
    previous_grades_listbox.delete(0, tk.END)
    for subject in previous_grades:
        previous_grades_listbox.insert(tk.END, f"{subject}: {round(previous_grades[subject] * 100, 3)}%")
    previous_grades_entry.delete(0, tk.END)
    previous_grades_entry.focus_set()


def add_current_grade():
    global current_grades
    subject, grade = current_grades_entry.get().split(":")
    subject = subject.strip().lower()
    grade = grade.strip()
    current_grades[subject] = float(grade) / 100
    current_grades_listbox.delete(0, tk.END)
    for subject in current_grades:
        current_grades_listbox.insert(tk.END, f"{subject}: {round(current_grades[subject] * 100, 3)}%")
    current_grades_entry.delete(0, tk.END)
    current_grades_entry.focus_set()


def clear_previous_grades():
    global previous_grades
    previous_grades = {}
    previous_grades_listbox.delete(0, tk.END)


def clear_current_grades():
    global current_grades
    current_grades = {}
    current_grades_listbox.delete(0, tk.END)


def run_assessment():
    authentication_username = username_entry.get()
    authentication_password = password_entry.get()
    username = instagram_entry.get()

    if authentication_username != "" and authentication_password != "" and username != "":
        try:
            instagram_bot.login(authentication_username, authentication_password)
        except:
            error_window = tk.Toplevel()
            error_window.title("Error")
            error_label = tk.Label(error_window,
                                   text="Error logging in. Please check your username and password. Leave these fields blank if you want to attempt to scan the account without any authentication.")
            error_label.pack(padx=10, pady=5)
            return

    if username != "":
        try:
            instagram_assessment_results = instagram_health_assessment(username)
        except:
            instagram_assessment_results = InstagramHealthAssessment(0, [
                InstagramHealthAssessment.AssessmentResult(
                    "(ERROR) No account found. Private accounts may not be accessible if you are not logged in. Additionally, Instagram may refuse to accept connections if you are not logged in.",
                    datetime.datetime.now(),
                    0)])
    else:
        instagram_assessment_results = InstagramHealthAssessment(0, [
            InstagramHealthAssessment.AssessmentResult("(ERROR) No account entered.", datetime.datetime.now(), 0)])

    grades_assessment_results = grades_health_assessment([previous_grades, current_grades])

    mental_health = instagram_assessment_results.overall_health_score + grades_assessment_results.overall_health_score

    results_window = tk.Toplevel()
    results_window.title("Results")

    results_label = tk.Label(results_window, text=f"Mental Health Level: {round(mental_health, 3)}")
    results_label.pack(padx=10)
    hint_label = tk.Label(results_window,
                          text="The higher the number, the better the mental health. Slightly negative numbers are not unusual, but very negative numbers may indicate that the person needs help.")
    hint_label.pack(padx=10, pady=5)

    if username != "":
        instagram_score_label = tk.Label(results_window,
                                         text=f"Instagram Positivity Score: {round(instagram_assessment_results.overall_health_score, 3)}")
        instagram_score_label.pack(padx=10)
        instagram_results_listbox = tk.Listbox(results_window)
        instagram_results_listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        instagram_results_listbox.insert(tk.END,
                                         f"{round(instagram_assessment_results.results[0].health_score, 3)}: {instagram_assessment_results.results[0].caption}")
        for result in itertools.islice(instagram_assessment_results.results, 1, None):
            instagram_results_listbox.insert(tk.END,
                                             f"{round(result.health_score, 3)}: ({result.date.date()}) {result.caption}")
    else:
        instagram_score_label = tk.Label(results_window, text="No Instagram account provided.")
        instagram_score_label.pack(padx=10, pady=5)

    if len(grades_assessment_results.results) > 0:
        grades_score_label = tk.Label(results_window, text=f"Grade Improvement Score: "
                                                           f"{round(grades_assessment_results.overall_health_score, 3)}")
        grades_score_label.pack(padx=10)
        grades_results_listbox = tk.Listbox(results_window)
        grades_results_listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        for result in grades_assessment_results.results:
            grades_results_listbox.insert(tk.END, f"{result.subject}: {round(result.change, 3)}")
    else:
        grades_score_label = tk.Label(results_window, text="No grades could be compared.")
        grades_score_label.pack(padx=10, pady=5)


root = tk.Tk()
root.title("Mental Health Assessment")

instagram_entry_label = tk.Label(root, text="Enter Instagram Username")
instagram_entry_label.grid(row=0, column=0, padx=10, pady=5, sticky="e")
instagram_entry = tk.Entry(root)
instagram_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

previous_grades_entry_label = tk.Label(root, text="Enter Previous Grade (subject:grade)")
previous_grades_entry_label.grid(row=1, column=0, padx=10, pady=5, sticky="e")
previous_grades_entry = tk.Entry(root)
previous_grades_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
previous_grades_entry.bind("<Return>", (lambda _: add_previous_grade()))
previous_grades_add_button = tk.Button(root, text="Add Grade", command=add_previous_grade)
previous_grades_add_button.grid(row=1, column=2, padx=10, pady=5)
previous_grades_clear_button = tk.Button(root, text="Clear Grades", command=clear_previous_grades)
previous_grades_clear_button.grid(row=2, column=2, padx=10, pady=5)

previous_grades_listbox_label = tk.Label(root, text="Previous Grades:")
previous_grades_listbox_label.grid(row=2, column=0, padx=10, pady=5, sticky="ne")
previous_grades_listbox = tk.Listbox(root)
previous_grades_listbox.grid(row=2, column=1, padx=10, pady=5, sticky="nsew")

current_grades_entry_label = tk.Label(root, text="Enter Current Grade (subject:grade)")
current_grades_entry_label.grid(row=1, column=3, padx=10, pady=5, sticky="e")
current_grades_entry = tk.Entry(root)
current_grades_entry.grid(row=1, column=4, padx=10, pady=5, sticky="ew")
current_grades_entry.bind("<Return>", (lambda _: add_current_grade()))
current_grades_add_button = tk.Button(root, text="Add Grade", command=add_current_grade)
current_grades_add_button.grid(row=1, column=5, padx=10, pady=5)
current_grades_clear_button = tk.Button(root, text="Clear Grades", command=clear_current_grades)
current_grades_clear_button.grid(row=2, column=5, padx=10, pady=5)

current_grades_listbox_label = tk.Label(root, text="Current Grades:")
current_grades_listbox_label.grid(row=2, column=3, padx=10, pady=5, sticky="ne")
current_grades_listbox = tk.Listbox(root)
current_grades_listbox.grid(row=2, column=4, padx=10, pady=5, sticky="nsew")

username_label = tk.Label(root, text="Your Instagram Username")
username_label.grid(row=3, column=0, padx=10, pady=5, sticky="e")
username_entry = tk.Entry(root)
username_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

password_label = tk.Label(root, text="Your Instagram Password")
password_label.grid(row=3, column=2, padx=10, pady=5, sticky="e")
password_entry = tk.Entry(root, show="*")
password_entry.grid(row=3, column=3, padx=10, pady=5, sticky="ew")

submit_button = tk.Button(root, text="Submit", command=run_assessment)
submit_button.grid(row=4, column=0, columnspan=6, padx=10, pady=5, sticky="ew")

root.rowconfigure(2, weight=1)
root.columnconfigure(1, weight=1)
root.columnconfigure(4, weight=1)

root.mainloop()
