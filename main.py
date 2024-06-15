import instaloader
import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from tensorflow.keras.layers import Dense
from tensorflow.keras.models import Sequential


def rateThreat(text):
    # Threat
    threatScore = 0

    # INSERT NEURAL NET HERE


def threat_assessment(username):
    # Get user information
    bot = instaloader.Instaloader()
    profile = instaloader.Profile.from_username(bot.context, username)

    # Threat
    threatScore = 0

    # Information
    biography = profile.biography
    threatScore += rateThreat(biography)

    # Posts
    posts = profile.get_posts()

    for post in posts:
        threatScore += rateThreat(post.caption)

    return threatScore


def notebook():
    model = Sequential()
    model.add(Dense(64, input_dim=num_features, activation='relu'))  # replace num_features
    model.add(Dense(64, activation='relu'))
    model.add(Dense(1, activation='sigmoid'))
    model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

    history = model.fit(X_train, Y_train, validation_data=(X_val, y_val), epochs=50,
                        batch_size=32)  # initialize X and Y train elsewhere
    test_loss, test_acc = model.evaluate(X_test, Y_test)

    print(f'Test accuracy: {test_acc}')

    model.save('mental_illness_risk_model.h5')

    num_samples = 1000

    age = np.random.normal(loc=35, scale=10, size=num_samples)
    gender = np.random.choice(['Male', 'Female', 'Other'], size=num_samples)
    education_level = np.random.choice(['High School', 'Bachelor', 'Master', 'PhD'], size=num_samples)

    sleep_hours = np.random.normal(loc=7, scale=1.5, size=num_samples)
    exercise_hours = np.random.normal(loc=3, scale=2, size=num_samples)
    substance_use = np.random.choice(['Never', 'Occasionally', 'Regularly'], size=num_samples)

    stress_levels = np.random.normal(loc=5, scale=2, size=num_samples)
    social_support = np.random.normal(loc=3, scale=1.5, size=num_samples)

    past_diagnoses = np.random.choice([0, 1], size=num_samples, p=[0.7, 0.3])
    family_history = np.random.choice([0, 1], size=num_samples, p=[0.8, 0.2])

    data = pd.DataFrame({
        'Age': age,
        'Gender': gender,
        'Education_Level': education_level,
        'Sleep_Hours': sleep_hours,
        'Exercise_Hours': exercise_hours,
        'Substance_Use': substance_use,
        'Stress_Levels': stress_levels,
        'Social_Support': social_support,
        'Past_Diagnoses': past_diagnoses,
        'Family_History': family_history
    })

    # Generates risk of mental illness based on logic
    data['Mental_Illness_Risk'] = (data['Stress_Levels'] > 6) | (data['Past_Diagnoses'] == 1) | (
            data['Family_History'] == 1)

    # One-hot encode categorical variables
    categorical_columns = ['Gender', 'Education_Level', 'Substance_Use']
    encoder = OneHotEncoder(sparse=False)
    encoded_categorical_data = encoder.fit_transform(data[categorical_columns])

    # Standardize numerical variables
    numerical_columns = ['Age', 'Sleep_Hours', 'Exercise_Hours', 'Stress_Levels', 'Social_Support']
    scaler = StandardScaler()
    scaled_numerical_data = scaler.fit_transform(data[numerical_columns])

    # Combine preprocessed data
    preprocessed_data = np.hstack([encoded_categorical_data, scaled_numerical_data])

    # Define target variable
    target = data['Mental_Illness_Risk'].astype(int)
