import csv
import dataclasses
import datetime
import itertools
import threading
import customtkinter as ctk
from customtkinter import *
import speech_recognition as sr
import tkinter as tk
import urllib
import urllib.request
from tkinter import filedialog, messagebox

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
recognizer = sr.Recognizer()


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


@dataclasses.dataclass
class TextHealthAssessment:
    student_text: str
    overall_health_score: float


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

    return GradesHealthAssessment(health_score * 2.5 / len(results), results) # Drops in grades need to be multiplied by 2 to highlight them more


root = CTk()
ctk.set_default_color_theme("dark-blue")
root.title("Social Scanner")
root.geometry("1400x700")
root.minsize(1200, 600)

student_names = set()
student_grades = {}
student_texts = {}
assessment_results = []

analyze_brightness = tk.BooleanVar()
analyze_images = tk.BooleanVar()

name_label = ctk.CTkLabel(root, text="Enter Name (real@insta)")
name_label.grid(row=0, column=0, padx=10, pady=5, sticky="e")
name_entry = ctk.CTkEntry(root)
name_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

students_listbox = tk.Listbox(root, exportselection=0)
students_listbox.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

def add_student():
    user_input = name_entry.get()

    try:
        real_name, username = user_input.split("@")
        real_name = real_name.strip()
        username = username.strip().lower()
    except:
        real_name = ""
        username = user_input.strip().lower()

    student_name = f"{real_name}@{username}"

    if student_name == "" or student_name == "@":
        messagebox.showwarning("Empty field.", "Please enter a name/account.")
        return

    student_names.add(student_name)
    student_grades[student_name] = [{}, {}]
    student_texts[student_name] = ""

    students_listbox.delete(0, tk.END)
    for student_name in student_names:
        students_listbox.insert(tk.END, student_name)

    name_entry.delete(0, tk.END)

    previous_grades_listbox.delete(0, tk.END)
    current_grades_listbox.delete(0, tk.END)
    text_input.delete("1.0", tk.END)

    text_input.configure(state=tk.DISABLED)
    previous_grades_entry.configure(state=tk.DISABLED)
    current_grades_entry.configure(state=tk.DISABLED)
    previous_grades_add_button.configure(state=tk.DISABLED)
    current_grades_add_button.configure(state=tk.DISABLED)

    text_input_label.grid_remove()
    text_input.grid_remove()
    previous_grades_entry_label.grid_remove()
    previous_grades_entry.grid_remove()
    previous_grades_add_button.grid_remove()
    previous_grades_listbox_label.grid_remove()
    previous_grades_listbox.grid_remove()
    previous_grades_clear_button.grid_remove()
    current_grades_entry_label.grid_remove()
    current_grades_entry.grid_remove()
    current_grades_add_button.grid_remove()
    current_grades_listbox_label.grid_remove()
    current_grades_listbox.grid_remove()
    current_grades_clear_button.grid_remove()

def remove_student():
    selected_index = students_listbox.curselection()
    if selected_index:
        student_names.remove(students_listbox.get(selected_index))
        student_grades.pop(students_listbox.get(selected_index), None)
        student_texts.pop(students_listbox.get(selected_index), None)

        students_listbox.delete(0, tk.END)
        for student_name in student_names:
            students_listbox.insert(tk.END, student_name)
    else:
        messagebox.showwarning("Nothing selected.", "Please select a student to remove.")

    previous_grades_listbox.delete(0, tk.END)
    current_grades_listbox.delete(0, tk.END)
    text_input.delete("1.0", tk.END)

    text_input.configure(state=tk.DISABLED)
    previous_grades_entry.configure(state=tk.DISABLED)
    current_grades_entry.configure(state=tk.DISABLED)
    previous_grades_add_button.configure(state=tk.DISABLED)
    current_grades_add_button.configure(state=tk.DISABLED)

    text_input_label.grid_remove()
    text_input.grid_remove()
    previous_grades_entry_label.grid_remove()
    previous_grades_entry.grid_remove()
    previous_grades_add_button.grid_remove()
    previous_grades_listbox_label.grid_remove()
    previous_grades_listbox.grid_remove()
    previous_grades_clear_button.grid_remove()
    current_grades_entry_label.grid_remove()
    current_grades_entry.grid_remove()
    current_grades_add_button.grid_remove()
    current_grades_listbox_label.grid_remove()
    current_grades_listbox.grid_remove()
    current_grades_clear_button.grid_remove()

def clear_students():
    student_names.clear()
    student_grades.clear()
    student_texts.clear()

    students_listbox.delete(0, tk.END)
    previous_grades_listbox.delete(0, tk.END)
    current_grades_listbox.delete(0, tk.END)
    text_input.delete("1.0", tk.END)

    text_input.configure(state=tk.DISABLED)
    previous_grades_entry.configure(state=tk.DISABLED)
    current_grades_entry.configure(state=tk.DISABLED)
    previous_grades_add_button.configure(state=tk.DISABLED)
    current_grades_add_button.configure(state=tk.DISABLED)

    text_input_label.grid_remove()
    text_input.grid_remove()
    previous_grades_entry_label.grid_remove()
    previous_grades_entry.grid_remove()
    previous_grades_add_button.grid_remove()
    previous_grades_listbox_label.grid_remove()
    previous_grades_listbox.grid_remove()
    previous_grades_clear_button.grid_remove()
    current_grades_entry_label.grid_remove()
    current_grades_entry.grid_remove()
    current_grades_add_button.grid_remove()
    current_grades_listbox_label.grid_remove()
    current_grades_listbox.grid_remove()
    current_grades_clear_button.grid_remove()

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
                student_name_unformatted, grades, text = line.split(":")

                try:
                    real_name, username = student_name_unformatted.split("@")
                    real_name = real_name.strip()
                    username = username.strip().lower()
                except:
                    real_name = ""
                    username = student_name_unformatted.strip().lower()

                student_name = f"{real_name}@{username}"

                if student_name == "" or student_name == "@":
                    continue

                student_names.add(student_name)

                try:
                    student_grades[student_name] = [{}, {}]
                    previous, current = grades.split(";")
                    for subject in previous.split(","):
                        subject, grade = subject.split("=")
                        student_grades[student_name][0][subject.strip().lower()] = float(
                            grade.strip()) / 100
                    for subject in current.split(","):
                        subject, grade = subject.split("=")
                        student_grades[student_name][1][subject.strip().lower()] = float(
                            grade.strip()) / 100
                except:
                    student_grades[student_name] = [{}, {}]

                student_texts[student_name] = text.strip()
            except:
                try:
                    student_name_unformatted, grades = line.split(":")

                    try:
                        real_name, username = student_name_unformatted.split("@")
                        real_name = real_name.strip()
                        username = username.strip().lower()
                    except:
                        real_name = ""
                        username = student_name_unformatted.strip().lower()

                    student_name = f"{real_name}@{username}"

                    if student_name == "" or student_name == "@":
                        continue

                    student_names.add(student_name)

                    try:
                        student_grades[student_name] = [{}, {}]
                        previous, current = grades.split(";")
                        for subject in previous.split(","):
                            subject, grade = subject.split("=")
                            student_grades[student_name][0][subject.strip().lower()] = float(
                                grade.strip()) / 100
                        for subject in current.split(","):
                            subject, grade = subject.split("=")
                            student_grades[student_name][1][subject.strip().lower()] = float(
                                grade.strip()) / 100
                    except:
                        student_grades[student_name] = [{}, {}]

                    student_texts[student_name] = ""

                except:
                    student_name_unformatted = line.strip()

                    try:
                        real_name, username = student_name_unformatted.split("@")
                        real_name = real_name.strip()
                        username = username.strip().lower()
                    except:
                        real_name = ""
                        username = student_name_unformatted.strip().lower()

                    student_name = f"{real_name}@{username}"

                    if student_name == "" or student_name == "@":
                        continue

                    student_names.add(student_name)
                    student_grades[student_name] = [{}, {}]
                    student_texts[student_name] = ""

    students_listbox.delete(0, tk.END)
    for user in student_names:
        students_listbox.insert(tk.END, user)

    previous_grades_listbox.delete(0, tk.END)
    current_grades_listbox.delete(0, tk.END)
    text_input.delete("1.0", tk.END)

    text_input.configure(state=tk.DISABLED)
    previous_grades_entry.configure(state=tk.DISABLED)
    current_grades_entry.configure(state=tk.DISABLED)
    previous_grades_add_button.configure(state=tk.DISABLED)
    current_grades_add_button.configure(state=tk.DISABLED)

    text_input_label.grid_remove()
    text_input.grid_remove()
    previous_grades_entry_label.grid_remove()
    previous_grades_entry.grid_remove()
    previous_grades_add_button.grid_remove()
    previous_grades_listbox_label.grid_remove()
    previous_grades_listbox.grid_remove()
    previous_grades_clear_button.grid_remove()
    current_grades_entry_label.grid_remove()
    current_grades_entry.grid_remove()
    current_grades_add_button.grid_remove()
    current_grades_listbox_label.grid_remove()
    current_grades_listbox.grid_remove()
    current_grades_clear_button.grid_remove()

def update_text():
    selected_index = students_listbox.curselection()
    if selected_index:
        text_input.configure(state=tk.NORMAL)
        previous_grades_entry.configure(state=tk.NORMAL)
        current_grades_entry.configure(state=tk.NORMAL)
        previous_grades_add_button.configure(state=tk.NORMAL)
        current_grades_add_button.configure(state=tk.NORMAL)

        text_input_label.grid()
        text_input.grid()
        previous_grades_entry_label.grid()
        previous_grades_entry.grid()
        previous_grades_add_button.grid()
        previous_grades_listbox_label.grid()
        previous_grades_listbox.grid()
        previous_grades_clear_button.grid()
        current_grades_entry_label.grid()
        current_grades_entry.grid()
        current_grades_add_button.grid()
        current_grades_listbox_label.grid()
        current_grades_listbox.grid()
        current_grades_clear_button.grid()

        selected_user = students_listbox.get(selected_index)
        student_texts[selected_user] = text_input.get("1.0", tk.END).strip()
    else:
        previous_grades_listbox.delete(0, tk.END)
        current_grades_listbox.delete(0, tk.END)
        text_input.delete("1.0", tk.END)

        text_input.configure(state=tk.DISABLED)
        previous_grades_entry.configure(state=tk.DISABLED)
        current_grades_entry.configure(state=tk.DISABLED)
        previous_grades_add_button.configure(state=tk.DISABLED)
        current_grades_add_button.configure(state=tk.DISABLED)

        text_input_label.grid_remove()
        text_input.grid_remove()
        previous_grades_entry_label.grid_remove()
        previous_grades_entry.grid_remove()
        previous_grades_add_button.grid_remove()
        previous_grades_listbox_label.grid_remove()
        previous_grades_listbox.grid_remove()
        previous_grades_clear_button.grid_remove()
        current_grades_entry_label.grid_remove()
        current_grades_entry.grid_remove()
        current_grades_add_button.grid_remove()
        current_grades_listbox_label.grid_remove()
        current_grades_listbox.grid_remove()
        current_grades_clear_button.grid_remove()
        
        messagebox.showwarning("No student selected.", "Please select a student.")

name_entry.bind("<Return>", (lambda _: add_student()))

add_instagram_user_button = ctk.CTkButton(root, text="Add Student", height=50,command=add_student)
add_instagram_user_button.grid(row=0, column=2, padx=10, pady=5, sticky="ew")

import_list_button = ctk.CTkButton(root, text="Import List", height=50,command=import_list)
import_list_button.grid(row=0, column=3, padx=10, pady=5, sticky="ew")

text_input_label = ctk.CTkLabel(root, text="Enter Student's Text")
text_input_label.grid(row=0, column=4, padx=10, pady=5, sticky="nw")

text_input = ctk.CTkTextbox(root)
text_input.grid(row=1, column=4, padx=10, pady=5, sticky="nesw")
text_input.bind("<KeyRelease>", (lambda _: update_text()))

remove_instagram_user_button = ctk.CTkButton(root, text="Remove Student",
                                         height=50,command=remove_student)
remove_instagram_user_button.grid(row=1, column=2, padx=10, pady=5, sticky="ew")

clear_instagram_users_button = ctk.CTkButton(root, text="Clear Students",
                                         height=50,command=clear_students)
clear_instagram_users_button.grid(row=1, column=3, padx=10, pady=5, sticky="ew")

previous_grades_listbox_label = ctk.CTkLabel(root, text="Previous Grades")
previous_grades_listbox_label.grid(row=3, column=0, padx=10, pady=5, sticky="ne")

previous_grades_listbox = tk.Listbox(root)
previous_grades_listbox.grid(row=3, column=1, padx=10, pady=5, sticky="nsew")

current_grades_listbox_label = ctk.CTkLabel(root, text="Current Grades")
current_grades_listbox_label.grid(row=3, column=3, padx=10, pady=5, sticky="ne")

current_grades_listbox = tk.Listbox(root)
current_grades_listbox.grid(row=3, column=4, padx=10, pady=5, sticky="nsew")

def update_user_info():
    selected_index = students_listbox.curselection()
    if selected_index:
        text_input.configure(state=tk.NORMAL)
        previous_grades_entry.configure(state=tk.NORMAL)
        current_grades_entry.configure(state=tk.NORMAL)
        previous_grades_add_button.configure(state=tk.NORMAL)
        current_grades_add_button.configure(state=tk.NORMAL)

        text_input_label.grid()
        text_input.grid()
        previous_grades_entry_label.grid()
        previous_grades_entry.grid()
        previous_grades_add_button.grid()
        previous_grades_listbox_label.grid()
        previous_grades_listbox.grid()
        previous_grades_clear_button.grid()
        current_grades_entry_label.grid()
        current_grades_entry.grid()
        current_grades_add_button.grid()
        current_grades_listbox_label.grid()
        current_grades_listbox.grid()
        current_grades_clear_button.grid()

        selected_user = students_listbox.get(selected_index)
        previous_grades_listbox.delete(0, tk.END)
        current_grades_listbox.delete(0, tk.END)
        text_input.delete("1.0", tk.END)

        try:
            for subject in student_grades[selected_user][0]:
                previous_grades_listbox.insert(tk.END,
                                                    f"{subject}: {round(student_grades[selected_user][0][subject] * 100, 3)}%")
            for subject in student_grades[selected_user][1]:
                current_grades_listbox.insert(tk.END,
                                                   f"{subject}: {round(student_grades[selected_user][1][subject] * 100, 3)}%")
        except:
            student_grades[selected_user] = [{}, {}]
            previous_grades_listbox.delete(0, tk.END)
            current_grades_listbox.delete(0, tk.END)

        try:
            text_input.insert(tk.END, student_texts[selected_user])
        except:
            student_texts[selected_user] = ""
            text_input.delete("1.0", tk.END)
    else:
        previous_grades_listbox.delete(0, tk.END)
        current_grades_listbox.delete(0, tk.END)
        text_input.delete("1.0", tk.END)

        text_input.configure(state=tk.DISABLED)
        previous_grades_entry.configure(state=tk.DISABLED)
        current_grades_entry.configure(state=tk.DISABLED)
        previous_grades_add_button.configure(state=tk.DISABLED)
        current_grades_add_button.configure(state=tk.DISABLED)

        text_input_label.grid_remove()
        text_input.grid_remove()
        previous_grades_entry_label.grid_remove()
        previous_grades_entry.grid_remove()
        previous_grades_add_button.grid_remove()
        previous_grades_listbox_label.grid_remove()
        previous_grades_listbox.grid_remove()
        previous_grades_clear_button.grid_remove()
        current_grades_entry_label.grid_remove()
        current_grades_entry.grid_remove()
        current_grades_add_button.grid_remove()
        current_grades_listbox_label.grid_remove()
        current_grades_listbox.grid_remove()
        current_grades_clear_button.grid_remove()

def add_previous_grade():
    selected_index = students_listbox.curselection()
    if selected_index:
        text_input.configure(state=tk.NORMAL)
        previous_grades_entry.configure(state=tk.NORMAL)
        current_grades_entry.configure(state=tk.NORMAL)
        previous_grades_add_button.configure(state=tk.NORMAL)
        current_grades_add_button.configure(state=tk.NORMAL)

        text_input_label.grid()
        text_input.grid()
        previous_grades_entry_label.grid()
        previous_grades_entry.grid()
        previous_grades_add_button.grid()
        previous_grades_listbox_label.grid()
        previous_grades_listbox.grid()
        previous_grades_clear_button.grid()
        current_grades_entry_label.grid()
        current_grades_entry.grid()
        current_grades_add_button.grid()
        current_grades_listbox_label.grid()
        current_grades_listbox.grid()
        current_grades_clear_button.grid()

        selected_user = students_listbox.get(selected_index)

        try:
            subject, grade = previous_grades_entry.get().split(":")
        except:
            messagebox.showwarning("Invalid format.", "Please enter a subject and grade separated by a colon.")
            return

        subject = subject.strip().lower()
        grade = grade.strip()

        try:
            grade_value = float(grade)

            if grade_value > 100 or grade_value < 0:
                messagebox.showwarning("Invalid grade.", "Please enter a valid grade between 0 and 100.")

            student_grades[selected_user][0][subject] = grade_value / 100
        except:
            messagebox.showwarning("Invalid grade.",
                                   "Please enter a valid grade as a number without any special characters.")
            return

        previous_grades_listbox.delete(0, tk.END)
        for subject in student_grades[selected_user][0]:
            previous_grades_listbox.insert(tk.END,
                                                f"{subject}: {round(student_grades[selected_user][0][subject] * 100, 3)}%")

        previous_grades_entry.delete(0, tk.END)
        previous_grades_entry.focus_set()
    else:
        previous_grades_listbox.delete(0, tk.END)
        current_grades_listbox.delete(0, tk.END)
        text_input.delete("1.0", tk.END)

        text_input.configure(state=tk.DISABLED)
        previous_grades_entry.configure(state=tk.DISABLED)
        current_grades_entry.configure(state=tk.DISABLED)
        previous_grades_add_button.configure(state=tk.DISABLED)
        current_grades_add_button.configure(state=tk.DISABLED)

        text_input_label.grid_remove()
        text_input.grid_remove()
        previous_grades_entry_label.grid_remove()
        previous_grades_entry.grid_remove()
        previous_grades_add_button.grid_remove()
        previous_grades_listbox_label.grid_remove()
        previous_grades_listbox.grid_remove()
        previous_grades_clear_button.grid_remove()
        current_grades_entry_label.grid_remove()
        current_grades_entry.grid_remove()
        current_grades_add_button.grid_remove()
        current_grades_listbox_label.grid_remove()
        current_grades_listbox.grid_remove()
        current_grades_clear_button.grid_remove()
        
        messagebox.showwarning("No student selected.", "Please select a student.")

def add_current_grade():
    selected_index = students_listbox.curselection()
    if selected_index:
        text_input.configure(state=tk.NORMAL)
        previous_grades_entry.configure(state=tk.NORMAL)
        current_grades_entry.configure(state=tk.NORMAL)
        previous_grades_add_button.configure(state=tk.NORMAL)
        current_grades_add_button.configure(state=tk.NORMAL)

        text_input_label.grid()
        text_input.grid()
        previous_grades_entry_label.grid()
        previous_grades_entry.grid()
        previous_grades_add_button.grid()
        previous_grades_listbox_label.grid()
        previous_grades_listbox.grid()
        previous_grades_clear_button.grid()
        current_grades_entry_label.grid()
        current_grades_entry.grid()
        current_grades_add_button.grid()
        current_grades_listbox_label.grid()
        current_grades_listbox.grid()
        current_grades_clear_button.grid()

        selected_user = students_listbox.get(selected_index)

        try:
            subject, grade = current_grades_entry.get().split(":")
        except:
            messagebox.showwarning("Invalid format.", "Please enter a subject and grade separated by a colon.")
            return

        subject = subject.strip().lower()
        grade = grade.strip()

        try:
            student_grades[selected_user][1][subject] = float(grade) / 100
        except:
            messagebox.showwarning("Invalid grade.",
                                   "Please enter a valid grade as a number without any special characters.")
            return

        current_grades_listbox.delete(0, tk.END)
        for subject in student_grades[selected_user][1]:
            current_grades_listbox.insert(tk.END,
                                               f"{subject}: {round(student_grades[selected_user][1][subject] * 100, 3)}%")

        current_grades_entry.delete(0, tk.END)
        current_grades_entry.focus_set()
    else:
        previous_grades_listbox.delete(0, tk.END)
        current_grades_listbox.delete(0, tk.END)
        text_input.delete("1.0", tk.END)

        text_input.configure(state=tk.DISABLED)
        previous_grades_entry.configure(state=tk.DISABLED)
        current_grades_entry.configure(state=tk.DISABLED)
        previous_grades_add_button.configure(state=tk.DISABLED)
        current_grades_add_button.configure(state=tk.DISABLED)

        text_input_label.grid_remove()
        text_input.grid_remove()
        previous_grades_entry_label.grid_remove()
        previous_grades_entry.grid_remove()
        previous_grades_add_button.grid_remove()
        previous_grades_listbox_label.grid_remove()
        previous_grades_listbox.grid_remove()
        previous_grades_clear_button.grid_remove()
        current_grades_entry_label.grid_remove()
        current_grades_entry.grid_remove()
        current_grades_add_button.grid_remove()
        current_grades_listbox_label.grid_remove()
        current_grades_listbox.grid_remove()
        current_grades_clear_button.grid_remove()

        messagebox.showwarning("No student selected.", "Please select a student.")

def clear_previous_grades():
    selected_index = students_listbox.curselection()
    if selected_index:
        text_input.configure(state=tk.NORMAL)
        previous_grades_entry.configure(state=tk.NORMAL)
        current_grades_entry.configure(state=tk.NORMAL)
        previous_grades_add_button.configure(state=tk.NORMAL)
        current_grades_add_button.configure(state=tk.NORMAL)

        text_input_label.grid()
        text_input.grid()
        previous_grades_entry_label.grid()
        previous_grades_entry.grid()
        previous_grades_add_button.grid()
        previous_grades_listbox_label.grid()
        previous_grades_listbox.grid()
        previous_grades_clear_button.grid()
        current_grades_entry_label.grid()
        current_grades_entry.grid()
        current_grades_add_button.grid()
        current_grades_listbox_label.grid()
        current_grades_listbox.grid()
        current_grades_clear_button.grid()

        selected_user = students_listbox.get(selected_index)
        student_grades[selected_user][0].clear()
        previous_grades_listbox.delete(0, tk.END)
    else:
        previous_grades_listbox.delete(0, tk.END)
        current_grades_listbox.delete(0, tk.END)
        text_input.delete("1.0", tk.END)

        text_input.configure(state=tk.DISABLED)
        previous_grades_entry.configure(state=tk.DISABLED)
        current_grades_entry.configure(state=tk.DISABLED)
        previous_grades_add_button.configure(state=tk.DISABLED)
        current_grades_add_button.configure(state=tk.DISABLED)

        text_input_label.grid_remove()
        text_input.grid_remove()
        previous_grades_entry_label.grid_remove()
        previous_grades_entry.grid_remove()
        previous_grades_add_button.grid_remove()
        previous_grades_listbox_label.grid_remove()
        previous_grades_listbox.grid_remove()
        previous_grades_clear_button.grid_remove()
        current_grades_entry_label.grid_remove()
        current_grades_entry.grid_remove()
        current_grades_add_button.grid_remove()
        current_grades_listbox_label.grid_remove()
        current_grades_listbox.grid_remove()
        current_grades_clear_button.grid_remove()

        messagebox.showwarning("No student selected.", "Please select a student.")

def clear_current_grades():
    selected_index = students_listbox.curselection()
    if selected_index:
        text_input.configure(state=tk.NORMAL)
        previous_grades_entry.configure(state=tk.NORMAL)
        current_grades_entry.configure(state=tk.NORMAL)
        previous_grades_add_button.configure(state=tk.NORMAL)
        current_grades_add_button.configure(state=tk.NORMAL)

        text_input_label.grid()
        text_input.grid()
        previous_grades_entry_label.grid()
        previous_grades_entry.grid()
        previous_grades_add_button.grid()
        previous_grades_listbox_label.grid()
        previous_grades_listbox.grid()
        previous_grades_clear_button.grid()
        current_grades_entry_label.grid()
        current_grades_entry.grid()
        current_grades_add_button.grid()
        current_grades_listbox_label.grid()
        current_grades_listbox.grid()
        current_grades_clear_button.grid()

        selected_user = students_listbox.get(selected_index)
        student_grades[selected_user][1].clear()
        current_grades_listbox.delete(0, tk.END)
    else:
        previous_grades_listbox.delete(0, tk.END)
        current_grades_listbox.delete(0, tk.END)
        text_input.delete("1.0", tk.END)

        text_input.configure(state=tk.DISABLED)
        previous_grades_entry.configure(state=tk.DISABLED)
        current_grades_entry.configure(state=tk.DISABLED)
        previous_grades_add_button.configure(state=tk.DISABLED)
        current_grades_add_button.configure(state=tk.DISABLED)

        text_input_label.grid_remove()
        text_input.grid_remove()
        previous_grades_entry_label.grid_remove()
        previous_grades_entry.grid_remove()
        previous_grades_add_button.grid_remove()
        previous_grades_listbox_label.grid_remove()
        previous_grades_listbox.grid_remove()
        previous_grades_clear_button.grid_remove()
        current_grades_entry_label.grid_remove()
        current_grades_entry.grid_remove()
        current_grades_add_button.grid_remove()
        current_grades_listbox_label.grid_remove()
        current_grades_listbox.grid_remove()
        current_grades_clear_button.grid_remove()

        messagebox.showwarning("No student selected.", "Please select a student.")

students_listbox.bind("<<ListboxSelect>>", lambda _: update_user_info())

previous_grades_entry_label = ctk.CTkLabel(root, text="Enter Previous Grade (subject:grade)")
previous_grades_entry_label.grid(row=2, column=0, padx=10, pady=5, sticky="e")
previous_grades_entry = ctk.CTkEntry(root)
previous_grades_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
previous_grades_entry.bind("<Return>", (lambda _: add_previous_grade()))

previous_grades_add_button = ctk.CTkButton(root, text="Add Grade", command=add_previous_grade)
previous_grades_add_button.grid(row=2, column=2, padx=10, pady=5, sticky="ew")

previous_grades_clear_button = ctk.CTkButton(root, text="Clear Grades", command=clear_previous_grades)
previous_grades_clear_button.grid(row=3, column=2, padx=10, pady=5, sticky="ew")

current_grades_entry_label = ctk.CTkLabel(root, text="Enter Current Grade (subject:grade)")
current_grades_entry_label.grid(row=2, column=3, padx=10, pady=5, sticky="e")
current_grades_entry = ctk.CTkEntry(root)
current_grades_entry.grid(row=2, column=4, padx=10, pady=5, sticky="ew")
current_grades_entry.bind("<Return>", (lambda _: add_current_grade()))

current_grades_add_button = ctk.CTkButton(root, text="Add Grade", command=add_current_grade)
current_grades_add_button.grid(row=2, column=5, padx=10, pady=5, sticky="ew")

current_grades_clear_button = ctk.CTkButton(root, text="Clear Grades", command=clear_current_grades)
current_grades_clear_button.grid(row=3, column=5, padx=10, pady=5, sticky="ew")

instagram_username_label = ctk.CTkLabel(root, text="Your Instagram Username")
instagram_username_label.grid(row=4, column=0, padx=10, pady=5, sticky="e")
instagram_username_entry = ctk.CTkEntry(root)
instagram_username_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

instagram_password_label = ctk.CTkLabel(root, text="Your Instagram Password")
instagram_password_label.grid(row=4, column=3, padx=10, pady=5, sticky="e")
instagram_password_entry = ctk.CTkEntry(root, show="*")
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
        csv_out.writerow(['display_name', 'username', 'overall_score', 'instagram_score', 'grades_score', 'text_score',
                          'instagram_results',
                          'grade_results', 'text_content'])

        for row in assessment_results:
            csv_out.writerow((row[0], row[1], row[2], row[3].overall_health_score, row[4].overall_health_score,
                              row[5].overall_health_score, row[3].results, row[4].results, row[5].student_text))

def show_details(current_selection):
    try:
        selected_user = assessment_results[current_selection[0]]
    except:
        messagebox.showwarning("Nothing selected.", "Please select a student to see details.")
        return

    details_window = tk.Toplevel()
    details_window.configure(bg = "gray12")
    details_window.geometry("400x300")
    if selected_user[0] == "":
        details_window.title("Details")
    else:
        details_window.title(f"Details for {selected_user[0]}")

    results_label = ctk.CTkLabel(details_window, text=f"Details for {selected_user[0]}")
    results_label.pack(padx=10)

    mental_health_label = ctk.CTkLabel(details_window, text=f"Mental Health Score: {round(selected_user[2], 3)}")
    mental_health_label.pack()

    if selected_user[2] < -0.5:
        mental_health_label.configure(text_color="red")
    elif selected_user[2] < 0:
        mental_health_label.configure(text_color="orange")
    elif 0 < selected_user[2] <= 0.5:
        mental_health_label.configure(text_color="yellow")
    elif selected_user[2] > 0.5:
        mental_health_label.configure(text_color="green")

    if selected_user[1] != "":
        instagram_score_label = ctk.CTkLabel(details_window,
                                         text=f"Instagram Positivity Score: {round(selected_user[3].overall_health_score, 3)}")
        instagram_score_label.pack(padx=10)
        if selected_user[3].overall_health_score < -0.5:
            instagram_score_label.configure(text_color="red")
        elif selected_user[3].overall_health_score < 0:
            instagram_score_label.configure(text_color="orange")
        elif 0 < selected_user[3].overall_health_score <= 0.5:
            instagram_score_label.configure(text_color="yellow")
        elif selected_user[3].overall_health_score > 0.5:
            instagram_score_label.configure(text_color="green")

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
        instagram_score_label = ctk.CTkLabel(details_window, text="No Instagram account provided.")
        instagram_score_label.pack(padx=10, pady=5)

    if len(selected_user[4].results) > 0:
        grades_score_label = ctk.CTkLabel(details_window, text=f"Grade Improvement Score: "
            f"{round(selected_user[4].overall_health_score, 3)}")
        grades_score_label.pack(padx=10)
        if selected_user[4].overall_health_score < -0.5:
            grades_score_label.configure(text_color="red")
        elif selected_user[4].overall_health_score < 0:
            grades_score_label.configure(text_color="orange")
        elif 0 < selected_user[4].overall_health_score <= 0.5:
            grades_score_label.configure(text_color="yellow")
        elif selected_user[4].overall_health_score > 0.5:
            grades_score_label.configure(text_color="green")

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
        grades_score_label = ctk.CTkLabel(details_window, text="No grades could be compared.")
        grades_score_label.pack(padx=10, pady=5)
    
    if selected_user[5].student_text != "":
        text_score_label = ctk.CTkLabel(details_window, text=f"Text Health Score: "
            f"{round(selected_user[5].overall_health_score, 3)}")
        text_score_label.pack(padx=10)
        if selected_user[5].overall_health_score < -0.5:
            text_score_label.configure(text_color="red")
        elif selected_user[5].overall_health_score < 0:
            text_score_label.configure(text_color="orange")
        elif 0 < selected_user[5].overall_health_score <= 0.5:
            text_score_label.configure(text_color="yellow")
        elif selected_user[5].overall_health_score > 0.5:
            text_score_label.configure(text_color="green")

        text_display_box = ctk.CTkTextbox(details_window)
        text_display_box.pack(padx=10, fill=tk.BOTH, expand=True)
        text_display_box.insert("1.0", selected_user[5].student_text)
        text_display_box.configure(state=tk.DISABLED)
    else:
        text_score_label = ctk.CTkLabel(details_window, text="No text was provided.")
        text_score_label.pack(padx=10, pady=5)

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
        grades_assessment_results = grades_health_assessment(student_grades[user_input])
    except:
        grades_assessment_results = GradesHealthAssessment(0.0, [])

    try:
        text_to_score = student_texts[user_input]

        if text_to_score != "":
            text_assessment_results = TextHealthAssessment(text_to_score, text_health_analysis(text_to_score) / 4)
        else:
            text_assessment_results = TextHealthAssessment("", 0.0)
    except:
        text_assessment_results = TextHealthAssessment("", 0.0)

    mental_health_components = []

    if not (len(instagram_assessment_results.results) == 0 or (len(instagram_assessment_results.results) == 1 and
                                                          (instagram_assessment_results.results[
                                                           0].caption.startswith(
                                                           "(WARNING)") or instagram_assessment_results.results[
                                                           0].caption.startswith("(ERROR)")))):
        mental_health_components.append(instagram_assessment_results.overall_health_score)
    
    if len(grades_assessment_results.results) != 0:
        mental_health_components.append(grades_assessment_results.overall_health_score)
    
    if text_assessment_results.student_text != "":
        mental_health_components.append(text_assessment_results.overall_health_score)

    if len(mental_health_components) == 0:
        mental_health = 0.0
    else:
        mental_health = sum(mental_health_components) / len(mental_health_components)

    assessment_results.append((display_name, username, mental_health, instagram_assessment_results,
                         grades_assessment_results, text_assessment_results))

    if len(assessment_results) == total_users:
        def sort_key(result):
            return result[2]

        assessment_results.sort(key=sort_key)

        results_window = tk.Toplevel()
        results_window.configure(bg = "gray12")
        results_window.geometry("400x300")
        results_window.title("Results Summary")

        results_label = ctk.CTkLabel(results_window, text="Results Summary", fg_color="black")
        results_label.pack(padx=10)

        results_listbox = tk.Listbox(results_window)
        results_listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        for result in assessment_results:
            results_listbox.insert(tk.END, f"{result[0]}: {round(result[2], 3)}")
            if result[2] < -0.5:
                results_listbox.itemconfig(tk.END, {'fg': 'red'})
            elif result[2] < 0:
                results_listbox.itemconfig(tk.END, {'fg': 'orange'})
            elif 0 < result[2] <= 0.5:
                results_listbox.itemconfig(tk.END, {'fg': 'yellow'})
            elif result[2] > 0.5:
                results_listbox.itemconfig(tk.END, {'fg': 'green'})

        show_more_button = ctk.CTkButton(results_window, text="Show Details", height=50,
                                     command=lambda: show_details(results_listbox.curselection()))
        show_more_button.pack(padx=10, pady=5)

        save_to_csv_button = ctk.CTkButton(results_window, text="Save to CSV", height=50,command=save_to_csv)
        save_to_csv_button.pack(padx=10, pady=5)

        results_window.rowconfigure(1, weight=1)

def run_mass_assessment():
    authentication_username = instagram_username_entry.get()
    authentication_password = instagram_password_entry.get()

    if authentication_username != "" and authentication_password == "":
        try:
            instagram_bot.load_session_from_file(authentication_username)
        except:
            messagebox.showwarning("Error loading session.",
                                   "The session file for this username could not be found. Please log in again with both your username and password or leave the authentication fields blank.")

    if authentication_username != "" and authentication_password != "":
        try:
            instagram_bot.login(authentication_username, authentication_password)
        except:
            messagebox.showwarning("Error logging in.",
                                   "Please check your username and password. Leave these fields blank if you want to attempt to scan the account without any authentication.")
            return

    if len(student_names) == 0:
        messagebox.showwarning("Insufficient entries.", "Please add at least one entry.")
        return

    assessment_results.clear()

    for username in student_names:
        threading.Thread(target=run_basic_health_assessment,
                         args=(username, len(student_names))).start()
        
def open_speech_window():
    global text_box, record_button

    speech_window = tk.Toplevel(root)
    speech_window.configure(bg = "gray12")
    speech_window.geometry("400x300")
    speech_window.title("Speech Recognition")

    text_box = ctk.CTkTextbox(master=speech_window, width=300, height=150, fg_color="white", text_color="black")
    text_box.pack(pady=20)

    record_button = ctk.CTkButton(master=speech_window, text="Start Recording", command=start_recording)
    record_button.pack(pady=10)

def start_recording():
    global record_button
    record_button.configure(state=ctk.DISABLED)
    threading.Thread(target=record_speech).start()

def record_speech():
    global text_box, record_button

    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        update_text_box("Listening...")
        audio = recognizer.listen(source)

        try:
            update_text_box("Recognizing speech...")
            text = recognizer.recognize_google(audio)
            update_text_box(f"Recognized text: {text}")
            update_text_box(f"Mental health score: {text_health_analysis(text)}")
        except sr.UnknownValueError:
            update_text_box("Could not understand the audio.")
        except sr.RequestError as e:
            update_text_box(f"Could not request results; {e}")

    record_button.configure(state=ctk.NORMAL)

def update_text_box(text):
    global text_box
    text_box.insert('end', text + '\n')
    text_box.see('end')

analyze_brightness_mass_checkbox = ctk.CTkCheckBox(root, text="Analyze Image Brightness (fast)",
                                                  variable=analyze_brightness, onvalue=True,
                                                  offvalue=False)
analyze_brightness_mass_checkbox.grid(row=5, column=0, columnspan=3, pady=5)

analyze_images_mass_checkbox = ctk.CTkCheckBox(root, text="Analyze Image Text (could take longer)",
                                              variable=analyze_images, onvalue=True,
                                              offvalue=False)
analyze_images_mass_checkbox.grid(row=5, column=3, columnspan=3, pady=5)

run_mass_assessment_button = ctk.CTkButton(root, text="Run Mass Assessment",
                                       command=run_mass_assessment)
run_mass_assessment_button.grid(row=6, column=0, columnspan=6, padx=10, pady=5, sticky="ew")

start_recording_button = ctk.CTkButton(root, text="Run Speech Assessment")
start_recording_button.configure(command=open_speech_window)
start_recording_button.grid(row=7, column=0, columnspan=6, padx=10, pady=5, sticky="ew")


text_input.configure(state=tk.DISABLED)
previous_grades_entry.configure(state=tk.DISABLED)
current_grades_entry.configure(state=tk.DISABLED)
previous_grades_add_button.configure(state=tk.DISABLED)
current_grades_add_button.configure(state=tk.DISABLED)

text_input_label.grid_remove()
text_input.grid_remove()
previous_grades_entry_label.grid_remove()
previous_grades_entry.grid_remove()
previous_grades_add_button.grid_remove()
previous_grades_listbox_label.grid_remove()
previous_grades_listbox.grid_remove()
previous_grades_clear_button.grid_remove()
current_grades_entry_label.grid_remove()
current_grades_entry.grid_remove()
current_grades_add_button.grid_remove()
current_grades_listbox_label.grid_remove()
current_grades_listbox.grid_remove()
current_grades_clear_button.grid_remove()

root.rowconfigure(1, weight=1)
root.columnconfigure(1, weight=1)
root.columnconfigure(4, weight=4)


if __name__ == '__main__':
    root.mainloop()
