import unittest

import main


class TestTextHealthAssessment(unittest.TestCase):
    def test_positivity(self):
        positive_text = "I love life. I am so happy. The world is beautiful."
        positive_results = main.text_health_analysis(positive_text)
        self.assertGreater(positive_results, 0.5)

    def test_negativity(self):
        negative_text = "I hate the world. I am so sad. Life is terrible."
        negative_results = main.text_health_analysis(negative_text)
        self.assertLess(negative_results, -0.5)


class TestInstagramHealthAssessment(unittest.TestCase):
    def test_positivity(self):
        main.analyze_brightness.set(True)
        main.analyze_images.set(True)
        six_am_success_results = main.instagram_health_assessment("6amsuccess")  # A page that posts motivational quotes
        self.assertGreater(six_am_success_results.overall_health_score, 0.5)

    def test_negativity(self):
        main.analyze_brightness.set(True)
        main.analyze_images.set(True)
        serial_killers_podcast_results = main.instagram_health_assessment(
            "serialkillerspodcast")  # A page written by a person obsessed with serial killers
        self.assertLess(serial_killers_podcast_results.overall_health_score, -0.5)


class TestGradesHealthAssessment(unittest.TestCase):
    def test_positivity(self):
        grade_improvement = [{"math": 0.5, "science": 0.6, "english": 0.7},
                             {"math": 0.7, "science": 0.7, "english": 0.7}]
        grade_improvement_results = main.grades_health_assessment(grade_improvement)
        self.assertAlmostEqual(grade_improvement_results.overall_health_score, 0.1)

    def test_negativity(self):
        grade_decline = [{"math": 0.7, "science": 0.7, "english": 0.7}, {"math": 0.5, "science": 0.6, "english": 0.7}]
        grade_decline_results = main.grades_health_assessment(grade_decline)
        self.assertAlmostEqual(grade_decline_results.overall_health_score, -0.1)


if __name__ == '__main__':
    unittest.main()
