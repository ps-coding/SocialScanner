import csv
import dataclasses
import datetime
import itertools
import threading
import tkinter as tk
import urllib
import urllib.request
from tkinter import filedialog
from tkinter import messagebox

import cv2
import easyocr
import instaloader
import nltk
import nltk.corpus
import nltk.sentiment
import nltk.tokenize
import numpy as np

sentiment_analyzer = nltk.sentiment.vader.SentimentIntensityAnalyzer()
instagram_bot = instaloader.Instaloader()
reader = easyocr.Reader(['en'])


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

    health_score = 0.0

    # Concerning words
    concerning_words = ['kill', 'die', 'death', 'hate', 'destroy', 'massacre',
                        'slaughter', 'depression', 'depressed', 'sad', 'sadness', 'suicide', 'murder', 'hatred',
                        'booze', 'drunk', 'beer', 'lie', 'liar', 'killer', 'murderer', 'bomb', 'shoot', 'bombing',
                        'shooting', 'shooter']

    # Highlight negative words, ignoring positive words
    for word in analyzer_text.split(" "):
        word_score = sentiment_analyzer.polarity_scores(word)
        if word_score["neg"] == 1:
            health_score += sentiment_analyzer.polarity_scores(word)["compound"] / 1.5

        # Particularly concerning words get an additional penalty
        if word in concerning_words:
            health_score -= 0.5

    # Incorporate the overall sentiment of the text as the most important factor
    health_score += sentiment_analyzer.polarity_scores(analyzer_text)["compound"] * 3

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

    health_score = 0.0
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
            full_text = post.caption
            current_health_score = text_health_analysis(full_text)

            if analyze_images.get() and -0.2 < current_health_score < 0.2:
                text_recognition = reader.readtext(post.url, detail=0, paragraph=True)
                full_text = " ".join(text_recognition) + " " + post.caption
                current_health_score = text_health_analysis(full_text)
                full_text = "<Scanned: " + " ".join(text_recognition) + "> " + post.caption

            if analyze_brightness.get():
                image_request = urllib.request.urlopen(post.url)
                image_array = np.asarray(bytearray(image_request.read()), dtype=np.uint8)
                image = cv2.imdecode(image_array, 0)
                brightness_factor = (np.mean(image) - 100) / 255
                current_health_score += brightness_factor
                full_text = f"[Brightness: {round(brightness_factor, 3)}] " + full_text

            results.append(
                InstagramHealthAssessment.AssessmentResult(full_text, post.date_utc, current_health_score))
            health_score += current_health_score * recency_factor
        elif analyze_images.get():
            text_recognition = reader.readtext(post.url, detail=0, paragraph=True)
            full_text = " ".join(text_recognition)
            current_health_score = text_health_analysis(full_text)
            full_text = "<Scanned: " + full_text + ">"

            results.append(
                InstagramHealthAssessment.AssessmentResult(full_text, post.date_utc, current_health_score))
            health_score += current_health_score * recency_factor

        recency_factor /= 1.5

    if len(results) == 0 or (len(results) == 1 and results[0].caption.strip() == "(BIO)"):
        return InstagramHealthAssessment(0.0,
                                         [InstagramHealthAssessment.AssessmentResult(
                                             "(WARNING) No information found. You may need to sign in to a friend's account to view private posts.",
                                             datetime.datetime.now(), 0.0)])

    if len(results) == 1:
        results[
            0].caption += " (WARNING) No posts found. This account may have private posts that can only be seen if you log in using a friend's account."

    NORMALIZATION_FACTOR = 4  # Approximately normalize the score to the same scale as the grades (-1 to 1).

    return InstagramHealthAssessment(health_score / (1 + ((((2 / 3) ** (len(results) - 1)) - 1) / ((2 / 3) - 1))) /
                                     NORMALIZATION_FACTOR,
                                     results)  # Use the geometric series formula because of the weighted average.


@dataclasses.dataclass
class GradesHealthAssessment:
    @dataclasses.dataclass
    class AssessmentResult:
        subject: str
        change: float

    overall_health_score: float
    results: list[AssessmentResult]


def grades_health_assessment(grades: list) -> GradesHealthAssessment:
    health_score = 0.0
    results = []

    for subject in grades[1]:
        if subject in grades[0]:
            difference = grades[1][subject] - grades[0][subject]
            results.append(GradesHealthAssessment.AssessmentResult(subject, difference))
            health_score += difference

    if len(results) == 0:
        return GradesHealthAssessment(0.0, results)

    return GradesHealthAssessment(health_score / len(results), results)


previous_grades = {}
current_grades = {}

mass_assessment_instagram_accounts = set()
mass_assessment_grades = {}

mass_results = []


def add_previous_grade():
    global previous_grades

    try:
        subject, grade = previous_grades_entry.get().split(":")
    except:
        messagebox.showwarning("Invalid format.", "Please enter a subject and grade separated by a colon.")
        return

    subject = subject.strip().lower()
    grade = grade.strip()

    try:
        previous_grades[subject] = float(grade) / 100
    except:
        messagebox.showwarning("Invalid grade.",
                               "Please enter a valid grade as a number without any special characters.")
        return

    previous_grades_listbox.delete(0, tk.END)
    for subject in previous_grades:
        previous_grades_listbox.insert(tk.END, f"{subject}: {round(previous_grades[subject] * 100, 3)}%")

    previous_grades_entry.delete(0, tk.END)
    previous_grades_entry.focus_set()


def add_current_grade():
    global current_grades

    try:
        subject, grade = current_grades_entry.get().split(":")
    except:
        messagebox.showwarning("Invalid format.", "Please enter a subject and grade separated by a colon.")
        return

    subject = subject.strip().lower()
    grade = grade.strip()

    try:
        current_grades[subject] = float(grade) / 100
    except:
        messagebox.showwarning("Invalid grade.",
                               "Please enter a valid grade as a number without any special characters.")
        return

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

    user_input = instagram_entry.get()
    try:
        real_name, username = user_input.split("@")
        real_name = real_name.strip()
        username = username.strip().lower()
    except:
        real_name = ""
        username = user_input.strip().lower()

    if username == "" and len(previous_grades) == 0 and len(current_grades) == 0:
        messagebox.showwarning("No data entered.", "Please enter an Instagram account and/or grades.")
        return

    if authentication_username != "" and authentication_password == "" and username != "":
        try:
            instagram_bot.load_session_from_file(authentication_username)
        except:
            messagebox.showwarning("Error loading session.",
                                   "The session file for this username could not be found. Please log in again or leave the authentication fields blank.")
            return

    if authentication_username != "" and authentication_password != "" and username != "":
        try:
            instagram_bot.login(authentication_username, authentication_password)
            instagram_bot.save_session_to_file()
        except:
            messagebox.showwarning("Error logging in.",
                                   "Please check your username and password. Leave these fields blank if you want to attempt to scan the account without any authentication. Leave the password field blank if you have logged in before.")
            return

    if username != "":
        try:
            instagram_assessment_results = instagram_health_assessment(username)
        except:
            instagram_assessment_results = InstagramHealthAssessment(0.0, [
                InstagramHealthAssessment.AssessmentResult(
                    "(ERROR) No account found. Instagram may refuse to accept connections if you are not logged in.",
                    datetime.datetime.now(),
                    0.0)])
    else:
        instagram_assessment_results = InstagramHealthAssessment(0.0, [
            InstagramHealthAssessment.AssessmentResult("(ERROR) No account entered.", datetime.datetime.now(), 0.0)])

    grades_assessment_results = grades_health_assessment([previous_grades, current_grades])

    if len(instagram_assessment_results.results) == 0 or (len(instagram_assessment_results.results) == 1 and
                                                          (instagram_assessment_results.results[0].caption.startswith(
                                                              "(WARNING)") or instagram_assessment_results.results[
                                                               0].caption.startswith("(ERROR)"))):
        mental_health = grades_assessment_results.overall_health_score
    elif len(grades_assessment_results.results) == 0:
        mental_health = instagram_assessment_results.overall_health_score
    else:
        mental_health = (instagram_assessment_results.overall_health_score +
                         grades_assessment_results.overall_health_score) / 2

    results_window = tk.Toplevel()
    if real_name == "" and username == "":
        results_window.title("Results")
    elif username == "":
        results_window.title(f"Results for {real_name}")
    else:
        results_window.title(f"Results for {real_name}@{username}")

    results_label = tk.Label(results_window, text=f"Mental Health Level: {round(mental_health, 3)}")
    if mental_health < -0.5:
        results_label.config(fg="red")
    elif mental_health < 0:
        results_label.config(fg="orange")
    elif 0 < mental_health <= 0.5:
        results_label.config(fg="yellow")
    elif mental_health > 0.5:
        results_label.config(fg="green")

    results_label.pack(padx=10)

    hint_label = tk.Label(results_window,
                          text="The higher the number, the better the mental health.\nUse this tool with judgement.")
    hint_label.pack(padx=10, pady=5)
    hint_label.bind('<Configure>', lambda _: hint_label.config(wraplength=hint_label.winfo_width()))

    if username != "":
        instagram_score_label = tk.Label(results_window,
                                         text=f"Instagram Positivity Score: {round(instagram_assessment_results.overall_health_score, 3)}")
        instagram_score_label.pack(padx=10)
        if instagram_assessment_results.overall_health_score < -0.5:
            instagram_score_label.config(fg="red")
        elif instagram_assessment_results.overall_health_score < 0:
            instagram_score_label.config(fg="orange")
        elif 0 < instagram_assessment_results.overall_health_score <= 0.5:
            instagram_score_label.config(fg="yellow")
        elif instagram_assessment_results.overall_health_score > 0.5:
            instagram_score_label.config(fg="green")

        instagram_results_listbox = tk.Listbox(results_window)
        instagram_results_listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        instagram_results_listbox.insert(tk.END,
                                         f"{round(instagram_assessment_results.results[0].health_score, 3)}: {instagram_assessment_results.results[0].caption}")
        if instagram_assessment_results.results[0].health_score < -0.5:
            instagram_results_listbox.itemconfig(tk.END, {'fg': 'red'})
        elif instagram_assessment_results.results[0].health_score < 0:
            instagram_results_listbox.itemconfig(tk.END, {'fg': 'orange'})
        elif 0 < instagram_assessment_results.results[0].health_score <= 0.5:
            instagram_results_listbox.itemconfig(tk.END, {'fg': 'yellow'})
        elif instagram_assessment_results.results[0].health_score > 0.5:
            instagram_results_listbox.itemconfig(tk.END, {'fg': 'green'})

        for result in itertools.islice(instagram_assessment_results.results, 1, None):
            instagram_results_listbox.insert(tk.END,
                                             f"{round(result.health_score, 3)}: ({result.date.date()}) {result.caption}")
            if result.health_score < -0.5:
                instagram_results_listbox.itemconfig(tk.END, {'fg': 'red'})
            elif result.health_score < 0:
                instagram_results_listbox.itemconfig(tk.END, {'fg': 'orange'})
            elif 0 < result.health_score <= 0.5:
                instagram_results_listbox.itemconfig(tk.END, {'fg': 'yellow'})
            elif result.health_score > 0.5:
                instagram_results_listbox.itemconfig(tk.END, {'fg': 'green'})
    else:
        instagram_score_label = tk.Label(results_window, text="No Instagram account provided.")
        instagram_score_label.pack(padx=10, pady=5)

    if len(grades_assessment_results.results) > 0:
        grades_score_label = tk.Label(results_window, text=f"Grade Improvement Score: "
                                                           f"{round(grades_assessment_results.overall_health_score, 3)}")
        grades_score_label.pack(padx=10)
        if grades_assessment_results.overall_health_score < -0.5:
            grades_score_label.config(fg="red")
        elif grades_assessment_results.overall_health_score < 0:
            grades_score_label.config(fg="orange")
        elif 0 < grades_assessment_results.overall_health_score <= 0.5:
            grades_score_label.config(fg="yellow")
        elif grades_assessment_results.overall_health_score > 0.5:
            grades_score_label.config(fg="green")

        grades_results_listbox = tk.Listbox(results_window)
        grades_results_listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        for result in grades_assessment_results.results:
            grades_results_listbox.insert(tk.END, f"{result.subject}: {round(result.change, 3)}")
            if result.change < -0.5:
                grades_results_listbox.itemconfig(tk.END, {'fg': 'red'})
            elif result.change < 0:
                grades_results_listbox.itemconfig(tk.END, {'fg': 'orange'})
            elif 0 < result.change <= 0.5:
                grades_results_listbox.itemconfig(tk.END, {'fg': 'yellow'})
            elif result.change > 0.5:
                grades_results_listbox.itemconfig(tk.END, {'fg': 'green'})
    else:
        grades_score_label = tk.Label(results_window, text="No grades could be compared.")
        grades_score_label.pack(padx=10, pady=5)


def launch_raw_text_assessment():
    raw_text_window = tk.Toplevel()
    raw_text_window.title("Raw Text Assessment")

    text_box = tk.Text(raw_text_window, height=10, width=40, wrap=tk.WORD)
    text_box.grid(row=0, column=0, padx=10, pady=10, sticky="nesw")

    result_label = tk.Label(raw_text_window, text="Type something to see the results.")
    result_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")

    def update_results():
        text_output = text_box.get("1.0", tk.END).strip()

        if text_output == "":
            result_label.config(text="Type something to see the results.", fg="gray")
            return

        if len(text_output) < 10:
            result_label.config(text="Type more to see the results.", fg="gray")
            return

        results = round(text_health_analysis(text_output) / 4, 3)
        result_label.config(text=results, fg="gray")

        if results < -0.5:
            result_label.config(fg="red")
        elif results < 0:
            result_label.config(fg="orange")
        elif 0 < results <= 0.5:
            result_label.config(fg="yellow")
        elif results > 0.5:
            result_label.config(fg="green")
        else:
            result_label.config(fg="gray")

    text_box.bind("<Key>", (lambda _: update_results()))
    text_box.bind("<Return>", (lambda _: update_results()))
    text_box.bind("<BackSpace>", (lambda _: update_results()))

    raw_text_window.rowconfigure(0, weight=1)
    raw_text_window.columnconfigure(0, weight=1)


def launch_mass_assessment():
    mass_assessment_window = tk.Toplevel()
    mass_assessment_window.title("Mass Assessment")

    instagram_user_label = tk.Label(mass_assessment_window, text="Enter Name/Instagram Username")
    instagram_user_label.grid(row=0, column=0, padx=10, pady=5, sticky="e")
    instagram_user_entry = tk.Entry(mass_assessment_window)
    instagram_user_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
    instagram_user_entry.insert(0, instagram_entry.get())

    instagram_user_listbox = tk.Listbox(mass_assessment_window)
    instagram_user_listbox.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
    for user in mass_assessment_instagram_accounts:
        instagram_user_listbox.insert(tk.END, user)

    def add_instagram_user():
        user_input = instagram_user_entry.get()

        try:
            real_name, username = user_input.split("@")
            real_name = real_name.strip()
            username = username.strip().lower()
        except:
            real_name = ""
            username = user_input.strip().lower()

        instagram_user = f"{real_name}@{username}"

        if instagram_user == "" or instagram_user == "@":
            messagebox.showwarning("Empty field.", "Please enter a name/account.")
            return

        mass_assessment_instagram_accounts.add(instagram_user)
        mass_assessment_grades[instagram_user] = [{}, {}]

        instagram_user_listbox.delete(0, tk.END)
        for user in mass_assessment_instagram_accounts:
            instagram_user_listbox.insert(tk.END, user)

        instagram_user_entry.delete(0, tk.END)

        user_previous_grades_listbox.delete(0, tk.END)
        user_current_grades_listbox.delete(0, tk.END)

    def remove_instagram_user():
        selected_index = instagram_user_listbox.curselection()
        if selected_index:
            mass_assessment_instagram_accounts.remove(instagram_user_listbox.get(selected_index))
            mass_assessment_grades.pop(instagram_user_listbox.get(selected_index), None)

            instagram_user_listbox.delete(0, tk.END)
            for user in mass_assessment_instagram_accounts:
                instagram_user_listbox.insert(tk.END, user)
        else:
            messagebox.showwarning("Nothing selected.", "Please select an account to remove.")

        user_previous_grades_listbox.delete(0, tk.END)
        user_current_grades_listbox.delete(0, tk.END)

    def clear_instagram_users():
        mass_assessment_instagram_accounts.clear()
        mass_assessment_grades.clear()

        instagram_user_listbox.delete(0, tk.END)
        user_previous_grades_listbox.delete(0, tk.END)
        user_current_grades_listbox.delete(0, tk.END)

    def import_list():
        list_file = filedialog.askopenfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        try:
            file = open(list_file)
        except:
            messagebox.showwarning("Invalid file.", "File could not be loaded.")
            return

        with file:
            for line in file:
                if line.strip() == "":
                    continue

                try:
                    user_input, grades = line.split(":")

                    try:
                        real_name, username = user_input.split("@")
                        real_name = real_name.strip()
                        username = username.strip().lower()
                    except:
                        real_name = ""
                        username = user_input.strip().lower()

                    account = f"{real_name}@{username}"

                    if account == "" or account == "@":
                        continue

                    mass_assessment_instagram_accounts.add(account)

                    try:
                        mass_assessment_grades[account] = [{}, {}]
                        previous, current = grades.split(";")
                        for subject in previous.split(","):
                            subject, grade = subject.split("=")
                            mass_assessment_grades[account][0][subject.strip().lower()] = float(
                                grade.strip()) / 100
                        for subject in current.split(","):
                            subject, grade = subject.split("=")
                            mass_assessment_grades[account][1][subject.strip().lower()] = float(
                                grade.strip()) / 100
                    except:
                        mass_assessment_grades[account] = [{}, {}]
                except:
                    user_input = line.strip()

                    try:
                        real_name, username = user_input.split("@")
                        real_name = real_name.strip()
                        username = username.strip().lower()
                    except:
                        real_name = ""
                        username = user_input.strip().lower()

                    name = f"{real_name}@{username}"

                    if name == "" or name == "@":
                        continue

                    mass_assessment_instagram_accounts.add(name)
                    mass_assessment_grades[name] = [{}, {}]

        instagram_user_listbox.delete(0, tk.END)
        for user in mass_assessment_instagram_accounts:
            instagram_user_listbox.insert(tk.END, user)

        user_previous_grades_listbox.delete(0, tk.END)
        user_current_grades_listbox.delete(0, tk.END)

    instagram_user_entry.bind("<Return>", (lambda _: add_instagram_user()))

    add_instagram_user_button = tk.Button(mass_assessment_window, text="Add Entry", command=add_instagram_user)
    add_instagram_user_button.grid(row=0, column=2, padx=10, pady=5, sticky="ew")

    import_list_button = tk.Button(mass_assessment_window, text="Import List", command=import_list)
    import_list_button.grid(row=0, column=3, padx=10, pady=5, sticky="ew")

    remove_instagram_user_button = tk.Button(mass_assessment_window, text="Remove Entry",
                                             command=remove_instagram_user)
    remove_instagram_user_button.grid(row=1, column=2, padx=10, pady=5, sticky="ew")

    clear_instagram_users_button = tk.Button(mass_assessment_window, text="Clear Entries",
                                             command=clear_instagram_users)
    clear_instagram_users_button.grid(row=1, column=3, padx=10, pady=5, sticky="ew")

    user_previous_grades_listbox_label = tk.Label(mass_assessment_window, text="Previous Grades:")
    user_previous_grades_listbox_label.grid(row=3, column=0, padx=10, pady=5, sticky="ne")

    user_previous_grades_listbox = tk.Listbox(mass_assessment_window)
    user_previous_grades_listbox.grid(row=3, column=1, padx=10, pady=5, sticky="nsew")

    user_current_grades_listbox_label = tk.Label(mass_assessment_window, text="Current Grades:")
    user_current_grades_listbox_label.grid(row=3, column=3, padx=10, pady=5, sticky="ne")

    user_current_grades_listbox = tk.Listbox(mass_assessment_window)
    user_current_grades_listbox.grid(row=3, column=4, padx=10, pady=5, sticky="nsew")

    def update_user_grades():
        selected_index = instagram_user_listbox.curselection()
        if selected_index:
            selected_user = instagram_user_listbox.get(selected_index)
            user_previous_grades_listbox.delete(0, tk.END)
            user_current_grades_listbox.delete(0, tk.END)
            try:
                for subject in mass_assessment_grades[selected_user][0]:
                    user_previous_grades_listbox.insert(tk.END,
                                                        f"{subject}: {round(mass_assessment_grades[selected_user][0][subject] * 100, 3)}%")
                for subject in mass_assessment_grades[selected_user][1]:
                    user_current_grades_listbox.insert(tk.END,
                                                       f"{subject}: {round(mass_assessment_grades[selected_user][1][subject] * 100, 3)}%")
            except:
                mass_assessment_grades[selected_user] = [{}, {}]
                user_previous_grades_listbox.delete(0, tk.END)
                user_current_grades_listbox.delete(0, tk.END)
        else:
            user_previous_grades_listbox.delete(0, tk.END)
            user_current_grades_listbox.delete(0, tk.END)

    def add_previous_grade():
        selected_index = instagram_user_listbox.curselection()
        if selected_index:
            selected_user = instagram_user_listbox.get(selected_index)

            try:
                subject, grade = previous_grades_entry.get().split(":")
            except:
                messagebox.showwarning("Invalid format.", "Please enter a subject and grade separated by a colon.")
                return

            subject = subject.strip().lower()
            grade = grade.strip()

            try:
                mass_assessment_grades[selected_user][0][subject] = float(grade) / 100
            except:
                messagebox.showwarning("Invalid grade.",
                                       "Please enter a valid grade as a number without any special characters.")
                return

            user_previous_grades_listbox.delete(0, tk.END)
            for subject in mass_assessment_grades[selected_user][0]:
                user_previous_grades_listbox.insert(tk.END,
                                                    f"{subject}: {round(mass_assessment_grades[selected_user][0][subject] * 100, 3)}%")

            previous_grades_entry.delete(0, tk.END)
            previous_grades_entry.focus_set()
        else:
            user_previous_grades_listbox.delete(0, tk.END)
            user_current_grades_listbox.delete(0, tk.END)
            messagebox.showwarning("No student selected.", "Please select a student.")

    def add_current_grade():
        selected_index = instagram_user_listbox.curselection()
        if selected_index:
            selected_user = instagram_user_listbox.get(selected_index)

            try:
                subject, grade = current_grades_entry.get().split(":")
            except:
                messagebox.showwarning("Invalid format.", "Please enter a subject and grade separated by a colon.")
                return

            subject = subject.strip().lower()
            grade = grade.strip()

            try:
                mass_assessment_grades[selected_user][1][subject] = float(grade) / 100
            except:
                messagebox.showwarning("Invalid grade.",
                                       "Please enter a valid grade as a number without any special characters.")
                return

            user_current_grades_listbox.delete(0, tk.END)
            for subject in mass_assessment_grades[selected_user][1]:
                user_current_grades_listbox.insert(tk.END,
                                                   f"{subject}: {round(mass_assessment_grades[selected_user][1][subject] * 100, 3)}%")

            current_grades_entry.delete(0, tk.END)
            current_grades_entry.focus_set()
        else:
            user_previous_grades_listbox.delete(0, tk.END)
            user_current_grades_listbox.delete(0, tk.END)
            messagebox.showwarning("No student selected.", "Please select a student.")

    def clear_previous_grades():
        selected_index = instagram_user_listbox.curselection()
        if selected_index:
            selected_user = instagram_user_listbox.get(selected_index)
            mass_assessment_grades[selected_user][0].clear()
            user_previous_grades_listbox.delete(0, tk.END)

    def clear_current_grades():
        selected_index = instagram_user_listbox.curselection()
        if selected_index:
            selected_user = instagram_user_listbox.get(selected_index)
            mass_assessment_grades[selected_user][1].clear()
            user_current_grades_listbox.delete(0, tk.END)

    instagram_user_listbox.bind("<<ListboxSelect>>", lambda _: update_user_grades())

    previous_grades_entry_label = tk.Label(mass_assessment_window, text="Enter Previous Grade (subject:grade)")
    previous_grades_entry_label.grid(row=2, column=0, padx=10, pady=5, sticky="e")
    previous_grades_entry = tk.Entry(mass_assessment_window)
    previous_grades_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
    previous_grades_entry.bind("<Return>", (lambda _: add_previous_grade()))

    previous_grades_add_button = tk.Button(mass_assessment_window, text="Add Grade", command=add_previous_grade)
    previous_grades_add_button.grid(row=2, column=2, padx=10, pady=5, sticky="ew")

    previous_grades_clear_button = tk.Button(mass_assessment_window, text="Clear Grades", command=clear_previous_grades)
    previous_grades_clear_button.grid(row=3, column=2, padx=10, pady=5, sticky="ew")

    current_grades_entry_label = tk.Label(mass_assessment_window, text="Enter Current Grade (subject:grade)")
    current_grades_entry_label.grid(row=2, column=3, padx=10, pady=5, sticky="e")
    current_grades_entry = tk.Entry(mass_assessment_window)
    current_grades_entry.grid(row=2, column=4, padx=10, pady=5, sticky="ew")
    current_grades_entry.bind("<Return>", (lambda _: add_current_grade()))

    current_grades_add_button = tk.Button(mass_assessment_window, text="Add Grade", command=add_current_grade)
    current_grades_add_button.grid(row=2, column=5, padx=10, pady=5, sticky="ew")

    current_grades_clear_button = tk.Button(mass_assessment_window, text="Clear Grades", command=clear_current_grades)
    current_grades_clear_button.grid(row=3, column=5, padx=10, pady=5, sticky="ew")

    instagram_username_label = tk.Label(mass_assessment_window, text="Your Instagram Username")
    instagram_username_label.grid(row=4, column=0, padx=10, pady=5, sticky="e")
    instagram_username_entry = tk.Entry(mass_assessment_window)
    instagram_username_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

    instagram_password_label = tk.Label(mass_assessment_window, text="Your Instagram Password")
    instagram_password_label.grid(row=4, column=3, padx=10, pady=5, sticky="e")
    instagram_password_entry = tk.Entry(mass_assessment_window, show="*")
    instagram_password_entry.grid(row=4, column=4, padx=10, pady=5, sticky="ew")

    def save_to_csv():
        location = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files",
                                                                                     "*.csv")])

        try:
            file = open(location, "w")
        except:
            messagebox.showwarning("Invalid file.", "Could not save file.")
            return

        with file:
            csv_out = csv.writer(file)
            csv_out.writerow(['display_name', 'username', 'overall_score', 'instagram_score', 'grades_score',
                              'instagram_results',
                              'grade_results'])

            for row in mass_results:
                csv_out.writerow((row[0], row[1], row[2], row[3].overall_health_score, row[4].overall_health_score,
                                  row[3].results, row[4].results))

    def show_details(current_selection):
        selected_user = mass_results[current_selection[0]]

        details_window = tk.Toplevel()
        if selected_user[0] == "":
            details_window.title("Details")
        else:
            details_window.title(f"Details for {selected_user[0]}")

        results_label = tk.Label(details_window, text=f"Details for {selected_user[0]}")
        results_label.pack(padx=10)

        mental_health_label = tk.Label(details_window, text=f"Mental Health Score: {round(selected_user[2], 3)}")
        mental_health_label.pack()

        if selected_user[2] < -0.5:
            mental_health_label.config(fg="red")
        elif selected_user[2] < 0:
            mental_health_label.config(fg="orange")
        elif 0 < selected_user[2] <= 0.5:
            mental_health_label.config(fg="yellow")
        elif selected_user[2] > 0.5:
            mental_health_label.config(fg="green")

        if selected_user[1] != "":
            instagram_score_label = tk.Label(details_window,
                                             text=f"Instagram Positivity Score: {round(selected_user[3].overall_health_score, 3)}")
            instagram_score_label.pack(padx=10)
            if selected_user[3].overall_health_score < -0.5:
                instagram_score_label.config(fg="red")
            elif selected_user[3].overall_health_score < 0:
                instagram_score_label.config(fg="orange")
            elif 0 < selected_user[3].overall_health_score <= 0.5:
                instagram_score_label.config(fg="yellow")
            elif selected_user[3].overall_health_score > 0.5:
                instagram_score_label.config(fg="green")

            instagram_results_listbox = tk.Listbox(details_window)
            instagram_results_listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
            instagram_results_listbox.insert(tk.END,
                                             f"{round(selected_user[3].results[0].health_score, 3)}: {selected_user[3].results[0].caption}")
            if selected_user[3].results[0].health_score < -0.5:
                instagram_results_listbox.itemconfig(tk.END, {'fg': 'red'})
            elif selected_user[3].results[0].health_score < 0:
                instagram_results_listbox.itemconfig(tk.END, {'fg': 'orange'})
            elif 0 < selected_user[3].results[0].health_score <= 0.5:
                instagram_results_listbox.itemconfig(tk.END, {'fg': 'yellow'})
            elif selected_user[3].results[0].health_score > 0.5:
                instagram_results_listbox.itemconfig(tk.END, {'fg': 'green'})

            for result in itertools.islice(selected_user[3].results, 1, None):
                instagram_results_listbox.insert(tk.END,
                                                 f"{round(result.health_score, 3)}: ({result.date.date()}) {result.caption}")
                if result.health_score < -0.5:
                    instagram_results_listbox.itemconfig(tk.END, {'fg': 'red'})
                elif result.health_score < 0:
                    instagram_results_listbox.itemconfig(tk.END, {'fg': 'orange'})
                elif 0 < result.health_score <= 0.5:
                    instagram_results_listbox.itemconfig(tk.END, {'fg': 'yellow'})
                elif result.health_score > 0.5:
                    instagram_results_listbox.itemconfig(tk.END, {'fg': 'green'})
        else:
            instagram_score_label = tk.Label(details_window, text="No Instagram account provided.")
            instagram_score_label.pack(padx=10, pady=5)

        if len(selected_user[4].results) > 0:
            grades_score_label = tk.Label(details_window, text=f"Grade Improvement Score: "
                                                               f"{round(selected_user[4].overall_health_score, 3)}")
            grades_score_label.pack(padx=10)
            if selected_user[4].overall_health_score < -0.5:
                grades_score_label.config(fg="red")
            elif selected_user[4].overall_health_score < 0:
                grades_score_label.config(fg="orange")
            elif 0 < selected_user[4].overall_health_score <= 0.5:
                grades_score_label.config(fg="yellow")
            elif selected_user[4].overall_health_score > 0.5:
                grades_score_label.config(fg="green")

            grades_results_listbox = tk.Listbox(details_window)
            grades_results_listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
            for result in selected_user[4].results:
                grades_results_listbox.insert(tk.END, f"{result.subject}: {round(result.change, 3)}")
                if result.change < -0.5:
                    grades_results_listbox.itemconfig(tk.END, {'fg': 'red'})
                elif result.change < 0:
                    grades_results_listbox.itemconfig(tk.END, {'fg': 'orange'})
                elif 0 < result.change <= 0.5:
                    grades_results_listbox.itemconfig(tk.END, {'fg': 'yellow'})
                elif result.change > 0.5:
                    grades_results_listbox.itemconfig(tk.END, {'fg': 'green'})
        else:
            grades_score_label = tk.Label(details_window, text="No grades could be compared.")
            grades_score_label.pack(padx=10, pady=5)

    def run_basic_health_assessment(user_input, total_users):
        try:
            real_name, username = user_input.split("@")
            real_name = real_name.strip()
            username = username.strip().lower()
        except:
            real_name = ""
            username = user_input.strip().lower()

        if real_name == "" and username == "":
            display_name = ""
        elif username == "":
            display_name = real_name
        else:
            display_name = f"{real_name}@{username}"

        if username != "":
            try:
                instagram_assessment_results = instagram_health_assessment(username)
            except:
                instagram_assessment_results = InstagramHealthAssessment(0.0, [
                    InstagramHealthAssessment.AssessmentResult(
                        "(ERROR) No account found. Instagram may refuse to accept connections if you are not logged in.",
                        datetime.datetime.now(),
                        0.0)])
        else:
            instagram_assessment_results = InstagramHealthAssessment(0.0, [
                InstagramHealthAssessment.AssessmentResult("(ERROR) No account entered.", datetime.datetime.now(),
                                                           0.0)])

        try:
            grades_assessment_results = grades_health_assessment(mass_assessment_grades[user_input])
        except:
            grades_assessment_results = GradesHealthAssessment(0.0, [])

        if len(instagram_assessment_results.results) == 0 or (len(instagram_assessment_results.results) == 1 and
                                                              (instagram_assessment_results.results[
                                                                   0].caption.startswith(
                                                                  "(WARNING)") or instagram_assessment_results.results[
                                                                   0].caption.startswith("(ERROR)"))):
            mental_health = grades_assessment_results.overall_health_score
        elif len(grades_assessment_results.results) == 0:
            mental_health = instagram_assessment_results.overall_health_score
        else:
            mental_health = (instagram_assessment_results.overall_health_score +
                             grades_assessment_results.overall_health_score) / 2

        mass_results.append((display_name, username, mental_health, instagram_assessment_results,
                             grades_assessment_results))

        if len(mass_results) == total_users:
            def sort_key(result):
                return result[2]

            mass_results.sort(key=sort_key)

            results_window = tk.Toplevel()
            results_window.title("Results Summary")

            results_label = tk.Label(results_window, text="Results Summary")
            results_label.pack(padx=10)

            results_listbox = tk.Listbox(results_window)
            results_listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
            for result in mass_results:
                results_listbox.insert(tk.END, f"{result[0]}: {round(result[2], 3)}")
                if result[2] < -0.5:
                    results_listbox.itemconfig(tk.END, {'fg': 'red'})
                elif result[2] < 0:
                    results_listbox.itemconfig(tk.END, {'fg': 'orange'})
                elif 0 < result[2] <= 0.5:
                    results_listbox.itemconfig(tk.END, {'fg': 'yellow'})
                elif result[2] > 0.5:
                    results_listbox.itemconfig(tk.END, {'fg': 'green'})

            show_more_button = tk.Button(results_window, text="Show Details",
                                         command=lambda: show_details(results_listbox.curselection()))
            show_more_button.pack(padx=10, pady=5)

            save_to_csv_button = tk.Button(results_window, text="Save to CSV", command=save_to_csv)
            save_to_csv_button.pack(padx=10, pady=5)

            results_window.rowconfigure(1, weight=1)

    def run_mass_assessment():
        authentication_username = instagram_username_entry.get()
        authentication_password = instagram_password_entry.get()

        if authentication_username != "" and authentication_password != "":
            try:
                instagram_bot.login(authentication_username, authentication_password)
            except:
                messagebox.showwarning("Error logging in.",
                                       "Please check your username and password. Leave these fields blank if you want to attempt to scan the account without any authentication.")
                return

        if len(mass_assessment_instagram_accounts) == 0:
            messagebox.showwarning("Insufficient entries.", "Please add at least one entry.")
            return

        mass_results.clear()

        for username in mass_assessment_instagram_accounts:
            threading.Thread(target=run_basic_health_assessment,
                             args=(username, len(mass_assessment_instagram_accounts))).start()

    analyze_brightness_mass_checkbox = tk.Checkbutton(mass_assessment_window, text="Analyze Image Brightness (fast)",
                                                      variable=analyze_brightness, onvalue=True,
                                                      offvalue=False)
    analyze_brightness_mass_checkbox.grid(row=5, column=0, columnspan=3, pady=5)

    analyze_images_mass_checkbox = tk.Checkbutton(mass_assessment_window, text="Analyze Image Text (could take longer)",
                                                  variable=analyze_images, onvalue=True,
                                                  offvalue=False)
    analyze_images_mass_checkbox.grid(row=5, column=3, columnspan=3, pady=5)

    run_mass_assessment_button = tk.Button(mass_assessment_window, text="Run Mass Assessment",
                                           command=run_mass_assessment)
    run_mass_assessment_button.grid(row=6, column=0, columnspan=6, padx=10, pady=5, sticky="ew")

    mass_assessment_window.rowconfigure(1, weight=1)
    mass_assessment_window.columnconfigure(0, weight=1)
    mass_assessment_window.columnconfigure(1, weight=1)


root = tk.Tk()
root.title("Social Scanner: Mental Health Assessment")

instagram_entry_label = tk.Label(root, text="Enter Name/Instagram Username")
instagram_entry_label.grid(row=0, column=0, padx=10, pady=5, sticky="e")
instagram_entry = tk.Entry(root)
instagram_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

previous_grades_entry_label = tk.Label(root, text="Enter Previous Grade (subject:grade)")
previous_grades_entry_label.grid(row=1, column=0, padx=10, pady=5, sticky="e")
previous_grades_entry = tk.Entry(root)
previous_grades_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
previous_grades_entry.bind("<Return>", (lambda _: add_previous_grade()))
previous_grades_add_button = tk.Button(root, text="Add Grade", command=add_previous_grade)
previous_grades_add_button.grid(row=1, column=2, padx=10, pady=5, sticky="ew")
previous_grades_clear_button = tk.Button(root, text="Clear Grades", command=clear_previous_grades)
previous_grades_clear_button.grid(row=2, column=2, padx=10, pady=5, sticky="ew")

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
current_grades_add_button.grid(row=1, column=5, padx=10, pady=5, sticky="ew")
current_grades_clear_button = tk.Button(root, text="Clear Grades", command=clear_current_grades)
current_grades_clear_button.grid(row=2, column=5, padx=10, pady=5, sticky="ew")

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

analyze_brightness = tk.BooleanVar()
analyze_brightness_checkbox = tk.Checkbutton(root, text="Analyze Image Brightness (fast)", variable=analyze_brightness,
                                             onvalue=True, offvalue=False)
analyze_brightness_checkbox.grid(row=4, column=0, columnspan=2, pady=5, sticky="e")

analyze_images = tk.BooleanVar()
analyze_images_checkbox = tk.Checkbutton(root, text="Analyze Image Text (could take longer)", variable=analyze_images,
                                         onvalue=True, offvalue=False)
analyze_images_checkbox.grid(row=4, column=2, columnspan=2, pady=5, sticky="e")

submit_button = tk.Button(root, text="Run Individual Assessment", command=run_assessment)
submit_button.grid(row=3, column=4, rowspan=2, columnspan=2, padx=10, pady=5, sticky="nesw")

mass_assessment_button = tk.Button(root, text="Configure Mass Assessment", command=launch_mass_assessment)
mass_assessment_button.grid(row=5, column=0, columnspan=6, padx=10, pady=5, sticky="ew")

raw_assessment_button = tk.Button(root, text="Raw Text Calculation", command=launch_raw_text_assessment)
raw_assessment_button.grid(row=6, column=0, columnspan=6, padx=10, pady=10, sticky="ew")

root.rowconfigure(2, weight=1)
root.columnconfigure(1, weight=1)
root.columnconfigure(4, weight=1)

if __name__ == '__main__':
    root.mainloop()
